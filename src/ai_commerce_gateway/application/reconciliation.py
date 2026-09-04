from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from ai_commerce_gateway.contracts.models import (
    ActorContext,
    ProviderLookupCommand,
    ReconcileTransactionCommand,
    TransactionView,
)
from ai_commerce_gateway.contracts.provider import ProviderService
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ActorType, TransactionState
from ai_commerce_gateway.domain.execution import PaymentAttempt
from ai_commerce_gateway.domain.reconciliation import (
    RECONCILABLE_STATES,
    ReconciliationOutcome,
)
from ai_commerce_gateway.domain.transactions import Transaction

Clock = Callable[[], datetime]


class ReconciliationRepository(Protocol):
    def lock_transaction(self, transaction_id: str) -> Transaction | None: ...
    def get_payment_attempt(self, transaction_id: str) -> PaymentAttempt | None: ...
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
        metadata: dict[str, str | None] | None = None,
    ) -> Transaction: ...


class ReconciliationUnitOfWork(Protocol):
    repository: ReconciliationRepository

    def __enter__(self) -> "ReconciliationUnitOfWork": ...
    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


UnitOfWorkFactory = Callable[[], ReconciliationUnitOfWork]


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
            if attempt is None or attempt.provider_order_id is None:
                # No order was ever created at the provider, or we crashed before saving the ID
                outcome = ReconciliationOutcome.ORDER_NOT_FOUND
                new_state = TransactionState.FAILED
                transaction = repository.transition(
                    transaction.id,
                    new_state,
                    actor_type=actor.actor_type,
                    actor_id=actor.actor_id,
                    reason_code=outcome.value,
                    correlation_id=actor.correlation_id,
                )
                return _transaction_view(transaction, attempt)

            # Query provider for order
            try:
                order_evidence = self._provider_service.lookup_order(
                    ProviderLookupCommand(provider_order_id=attempt.provider_order_id)
                )
            except Exception:
                # If lookup fails (network issue, provider down), stay in RECONCILING or revert to UNKNOWN
                # B6 specifies RECONCILING mechanics, we revert to UNKNOWN so it can be retried later
                transaction = repository.transition(
                    transaction.id,
                    TransactionState.UNKNOWN,
                    actor_type=actor.actor_type,
                    actor_id=actor.actor_id,
                    reason_code=ReconciliationOutcome.PROVIDER_LOOKUP_FAILED.value,
                    correlation_id=actor.correlation_id,
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
                        if payment_evidence.capture_state == "captured":
                            outcome = ReconciliationOutcome.PAYMENT_CAPTURED
                            new_state = TransactionState.SUCCEEDED
                        else:
                            outcome = ReconciliationOutcome.PAYMENT_FAILED
                            new_state = TransactionState.FAILED
                    except Exception:
                        # Lookup failed, revert to UNKNOWN
                        transaction = repository.transition(
                            transaction.id,
                            TransactionState.UNKNOWN,
                            actor_type=actor.actor_type,
                            actor_id=actor.actor_id,
                            reason_code=ReconciliationOutcome.PROVIDER_LOOKUP_FAILED.value,
                            correlation_id=actor.correlation_id,
                        )
                        return _transaction_view(transaction, attempt)
                else:
                    # Order is paid but we don't have the payment ID.
                    # We can't succeed yet because D-010 requires explicit capture confirmation.
                    # Revert to PAYMENT_PENDING so webhook can supply the payment ID.
                    outcome = ReconciliationOutcome.ORDER_CREATED_NO_PAYMENT
                    new_state = TransactionState.PAYMENT_PENDING
            elif order_evidence.provider_order_state in {"created", "attempted"}:
                outcome = ReconciliationOutcome.ORDER_CREATED_NO_PAYMENT
                new_state = TransactionState.PAYMENT_PENDING
            else:
                outcome = ReconciliationOutcome.ORDER_NOT_FOUND
                new_state = TransactionState.FAILED

            transaction = repository.transition(
                transaction.id,
                new_state,
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
                reason_code=outcome.value,
                correlation_id=actor.correlation_id,
                provider_reference_redacted=_redact(attempt.provider_order_id),
                metadata={
                    "provider": attempt.provider.value,
                    "provider_order_state": order_evidence.provider_order_state,
                },
            )
            return _transaction_view(transaction, attempt)


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
