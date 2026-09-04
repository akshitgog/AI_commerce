from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from ai_commerce_gateway.contracts.models import (
    ActorContext,
    CreateProviderOrderCommand,
    Money,
    ProviderLookupCommand,
    ProviderObservation,
    ReconcileTransactionCommand,
    TransactionView,
)
from ai_commerce_gateway.contracts.provider import ProviderService
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ActorType, TransactionState
from ai_commerce_gateway.domain.execution import PaymentAttempt
from ai_commerce_gateway.domain.provider_verification import ProviderEvidence
from ai_commerce_gateway.domain.reconciliation import (
    RECONCILABLE_STATES,
    ReconciliationOutcome,
)
from ai_commerce_gateway.domain.transactions import Transaction

Clock = Callable[[], datetime]


class ReconciliationRepository(Protocol):
    def lock_transaction(self, transaction_id: str) -> Transaction | None: ...
    def get_payment_attempt(self, transaction_id: str) -> PaymentAttempt | None: ...
    def save_provider_observation(
        self, attempt_id: str, observation: ProviderObservation
    ) -> PaymentAttempt: ...
    def transition(
        self,
        transaction_id: str,
        new_state: TransactionState,
        *,
        actor_type: ActorType,
        actor_id: str | None,
        reason_code: str,
        correlation_id: str,
        provider_reference_redacted: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Transaction: ...


class ReconciliationUnitOfWork(Protocol):
    repository: ReconciliationRepository

    def __enter__(self) -> "ReconciliationUnitOfWork": ...
    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


UnitOfWorkFactory = Callable[[], ReconciliationUnitOfWork]


@runtime_checkable
class ReceiptOrderLookupProvider(Protocol):
    """Optional internal capability for recovering a lost create-order response."""

    def lookup_order_by_receipt(
        self, command: CreateProviderOrderCommand
    ) -> ProviderObservation: ...


class TransactionReconciliationApplicationService:
    """Recover transaction state after dispatch uncertainty."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        provider_service: ProviderService,
        *,
        clock: Clock | None = None,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._provider_service = provider_service
        self._clock = clock or (lambda: datetime.now(UTC))

    def reconcile(
        self, command: ReconcileTransactionCommand, actor: ActorContext
    ) -> TransactionView:
        _require_system_actor(actor)

        # 1. Lock and transition to RECONCILING
        with self._unit_of_work_factory() as unit_of_work:
            repository = unit_of_work.repository
            transaction = repository.lock_transaction(command.transaction_id)
            if transaction is None:
                raise AppError(ErrorCode.NOT_FOUND, "Transaction not found.", status_code=404)

            if transaction.state not in RECONCILABLE_STATES:
                # Already resolved or not in a state needing reconciliation
                attempt = repository.get_payment_attempt(transaction.id)
                return _transaction_view(transaction, attempt)

            transaction = repository.transition(
                transaction.id,
                TransactionState.RECONCILING,
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
                reason_code="RECONCILIATION_STARTED",
                correlation_id=actor.correlation_id,
                metadata=_audit_scope(transaction),
            )

        # 2. Inspect attempt and query provider
        with self._unit_of_work_factory() as unit_of_work:
            repository = unit_of_work.repository
            # Need to lock again since we are in a new transaction
            transaction = repository.lock_transaction(command.transaction_id)
            if transaction is None or transaction.state is not TransactionState.RECONCILING:
                raise AppError(
                    ErrorCode.INVALID_STATE,
                    "Transaction state changed unexpectedly.",
                    status_code=409,
                )

            attempt = repository.get_payment_attempt(transaction.id)
            recovered_by_receipt = False
            if attempt is None:
                # Missing local evidence cannot prove that the provider did not receive a
                # dispatch. Preserve uncertainty and require operator investigation.
                transaction = repository.transition(
                    transaction.id,
                    TransactionState.UNKNOWN,
                    actor_type=actor.actor_type,
                    actor_id=actor.actor_id,
                    reason_code="PAYMENT_ATTEMPT_MISSING",
                    correlation_id=actor.correlation_id,
                    metadata=_audit_scope(transaction),
                )
                return _transaction_view(transaction, attempt)

            if attempt.provider_order_id is None:
                attempt = self._recover_order_by_receipt(
                    repository=repository,
                    transaction=transaction,
                    attempt=attempt,
                    actor=actor,
                )
                if attempt.provider_order_id is None:
                    current = repository.lock_transaction(transaction.id)
                    if current is None:
                        raise AppError(
                            ErrorCode.NOT_FOUND, "Transaction not found.", status_code=404
                        )
                    return _transaction_view(current, attempt)
                recovered_by_receipt = True

            # Query provider for order
            try:
                order_evidence = self._provider_service.lookup_order(
                    ProviderLookupCommand(provider_order_id=attempt.provider_order_id)
                )
                order_evidence = _require_trusted_order_evidence(
                    order_evidence,
                    transaction=transaction,
                    attempt=attempt,
                )
                attempt = repository.save_provider_observation(
                    attempt.id,
                    _merge_order_evidence(attempt, order_evidence),
                )
            except Exception:
                # A failed read cannot establish provider truth. Return to UNKNOWN so
                # reconciliation may safely retry the read later.
                transaction = repository.transition(
                    transaction.id,
                    TransactionState.UNKNOWN,
                    actor_type=actor.actor_type,
                    actor_id=actor.actor_id,
                    reason_code=ReconciliationOutcome.PROVIDER_LOOKUP_FAILED.value,
                    correlation_id=actor.correlation_id,
                    metadata=_audit_scope(transaction),
                )
                return _transaction_view(transaction, attempt)

            if order_evidence.provider_order_state == "paid":
                if attempt.provider_payment_id:
                    try:
                        payment_evidence = self._provider_service.lookup_payment(
                            ProviderLookupCommand(
                                provider_order_id=attempt.provider_order_id,
                                provider_payment_id=attempt.provider_payment_id,
                            )
                        )
                        payment_evidence = _require_trusted_payment_evidence(
                            payment_evidence,
                            transaction=transaction,
                            attempt=attempt,
                        )
                        attempt = repository.save_provider_observation(
                            attempt.id,
                            _merge_payment_evidence(
                                attempt,
                                order_evidence,
                                payment_evidence,
                            ),
                        )
                        if (
                            payment_evidence.provider_payment_state == "captured"
                            and payment_evidence.capture_state == "captured"
                        ):
                            outcome = ReconciliationOutcome.PAYMENT_CAPTURED
                            new_state = TransactionState.SUCCEEDED
                        elif payment_evidence.provider_payment_state in {"failed", "refunded"}:
                            outcome = ReconciliationOutcome.PAYMENT_FAILED
                            new_state = TransactionState.FAILED
                        else:
                            outcome = ReconciliationOutcome.ORDER_CREATED_NO_PAYMENT
                            new_state = TransactionState.PAYMENT_PENDING
                    except Exception:
                        # Lookup failed, revert to UNKNOWN
                        transaction = repository.transition(
                            transaction.id,
                            TransactionState.UNKNOWN,
                            actor_type=actor.actor_type,
                            actor_id=actor.actor_id,
                            reason_code=ReconciliationOutcome.PROVIDER_LOOKUP_FAILED.value,
                            correlation_id=actor.correlation_id,
                            metadata=_audit_scope(transaction),
                        )
                        return _transaction_view(transaction, attempt)
                else:
                    # Order is paid but we don't have the payment ID.
                    # We can't succeed yet because D-011 requires explicit capture confirmation.
                    # Revert to PAYMENT_PENDING so webhook can supply the payment ID.
                    outcome = ReconciliationOutcome.ORDER_CREATED_NO_PAYMENT
                    new_state = TransactionState.PAYMENT_PENDING
            elif order_evidence.provider_order_state in {"created", "attempted"}:
                outcome = ReconciliationOutcome.ORDER_CREATED_NO_PAYMENT
                new_state = TransactionState.PAYMENT_PENDING
            else:
                outcome = ReconciliationOutcome.PROVIDER_LOOKUP_FAILED
                new_state = TransactionState.UNKNOWN

            transaction = repository.transition(
                transaction.id,
                new_state,
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
                reason_code=outcome.value,
                correlation_id=actor.correlation_id,
                provider_reference_redacted=_redact(attempt.provider_order_id),
                metadata={
                    **_audit_scope(transaction),
                    "provider": attempt.provider.value,
                    "provider_order_state": order_evidence.provider_order_state,
                    "recovery_method": (
                        "transaction_receipt" if recovered_by_receipt else None
                    ),
                    "provider_payment_state": (
                        payment_evidence.provider_payment_state
                        if order_evidence.provider_order_state == "paid"
                        and attempt.provider_payment_id
                        else None
                    ),
                },
            )
            return _transaction_view(transaction, attempt)

    def _recover_order_by_receipt(
        self,
        *,
        repository: ReconciliationRepository,
        transaction: Transaction,
        attempt: PaymentAttempt,
        actor: ActorContext,
    ) -> PaymentAttempt:
        if not isinstance(self._provider_service, ReceiptOrderLookupProvider):
            repository.transition(
                transaction.id,
                TransactionState.UNKNOWN,
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
                reason_code="RECEIPT_LOOKUP_UNAVAILABLE",
                correlation_id=actor.correlation_id,
                metadata=_audit_scope(transaction),
            )
            return attempt

        command = CreateProviderOrderCommand(
            transaction_id=transaction.id,
            attempt_id=attempt.id,
            amount=Money(
                amount_minor=transaction.amount_minor,
                currency=transaction.currency,
            ),
            receipt=transaction.id,
            request_fingerprint=attempt.provider_request_fingerprint,
        )
        try:
            observation = self._provider_service.lookup_order_by_receipt(command)
            if (
                observation.provider is not attempt.provider
                or observation.provider_order_id is None
                or not observation.authenticity_verified
            ):
                raise ValueError("receipt lookup returned incomplete provider evidence")
        except Exception:
            repository.transition(
                transaction.id,
                TransactionState.UNKNOWN,
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
                reason_code=ReconciliationOutcome.PROVIDER_LOOKUP_FAILED.value,
                correlation_id=actor.correlation_id,
                metadata=_audit_scope(transaction),
            )
            return attempt

        return repository.save_provider_observation(attempt.id, observation)


def _require_system_actor(actor: ActorContext) -> None:
    if actor.actor_type is not ActorType.SYSTEM:
        raise AppError(
            ErrorCode.FORBIDDEN, "System identity required for reconciliation.", status_code=403
        )


def _redact(reference: str | None) -> str | None:
    return f"...{reference[-4:]}" if reference else None


def _transaction_view(transaction: Transaction, attempt: PaymentAttempt | None) -> TransactionView:
    from ai_commerce_gateway.contracts.models import Money, ProviderPhase

    provider_phase = None
    if attempt is not None:
        provider_phase = ProviderPhase(
            provider=attempt.provider,
            order_state=attempt.provider_order_state,
            payment_state=attempt.provider_payment_state,
            capture_state=attempt.capture_state,
            last_verified_at=attempt.last_verified_at,
        )
    return TransactionView(
        id=transaction.id,
        proposal_id=transaction.proposal_id,
        merchant_id=transaction.merchant_id,
        buyer_id=transaction.buyer_id,
        amount=Money(amount_minor=transaction.amount_minor, currency=transaction.currency),
        state=transaction.state,
        provider_phase=provider_phase,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
    )


def _require_trusted_order_evidence(
    observation: ProviderObservation,
    *,
    transaction: Transaction,
    attempt: PaymentAttempt,
) -> ProviderEvidence:
    if not isinstance(observation, ProviderEvidence):
        raise ValueError("order lookup did not return money-bearing provider evidence")
    expected = Money(amount_minor=transaction.amount_minor, currency=transaction.currency)
    if (
        not observation.authenticity_verified
        or observation.provider is not attempt.provider
        or observation.provider_order_id != attempt.provider_order_id
        or observation.provider_amount != expected
    ):
        raise ValueError("order lookup evidence does not match the transaction")
    return observation


def _require_trusted_payment_evidence(
    observation: ProviderObservation,
    *,
    transaction: Transaction,
    attempt: PaymentAttempt,
) -> ProviderEvidence:
    if not isinstance(observation, ProviderEvidence):
        raise ValueError("payment lookup did not return money-bearing provider evidence")
    expected = Money(amount_minor=transaction.amount_minor, currency=transaction.currency)
    if (
        not observation.authenticity_verified
        or observation.provider is not attempt.provider
        or observation.provider_order_id != attempt.provider_order_id
        or observation.provider_payment_id != attempt.provider_payment_id
        or observation.provider_amount != expected
    ):
        raise ValueError("payment lookup evidence does not match the transaction")
    return observation


def _merge_order_evidence(
    attempt: PaymentAttempt, observation: ProviderEvidence
) -> ProviderEvidence:
    return ProviderEvidence(
        provider=attempt.provider,
        provider_amount=observation.provider_amount,
        provider_order_id=observation.provider_order_id,
        provider_payment_id=attempt.provider_payment_id,
        provider_order_state=observation.provider_order_state,
        provider_payment_state=attempt.provider_payment_state,
        capture_state=attempt.capture_state,
        authenticity_verified=observation.authenticity_verified,
        observed_at=observation.observed_at,
        observation_source=observation.observation_source,
    )


def _merge_payment_evidence(
    attempt: PaymentAttempt,
    order: ProviderEvidence,
    payment: ProviderEvidence,
) -> ProviderEvidence:
    return ProviderEvidence(
        provider=attempt.provider,
        provider_amount=payment.provider_amount,
        provider_order_id=order.provider_order_id,
        provider_payment_id=payment.provider_payment_id,
        provider_order_state=order.provider_order_state,
        provider_payment_state=payment.provider_payment_state,
        capture_state=payment.capture_state,
        authenticity_verified=(order.authenticity_verified and payment.authenticity_verified),
        observed_at=max(order.observed_at, payment.observed_at),
        observation_source="reconciliation_order_and_payment_lookup",
    )


def _audit_scope(transaction: Transaction) -> dict[str, str | int | None]:
    return {
        "proposal_id": transaction.proposal_id,
        "buyer_authorization_id": transaction.buyer_authorization_id,
        "merchant_decision_id": transaction.merchant_decision_id,
        "merchant_id": transaction.merchant_id,
        "buyer_id": transaction.buyer_id,
        "amount_minor": transaction.amount_minor,
        "currency": transaction.currency,
    }
