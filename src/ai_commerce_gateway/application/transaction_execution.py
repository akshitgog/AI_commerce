import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from ai_commerce_gateway.contracts.models import (
    ActorContext,
    CreateProviderOrderCommand,
    ExecuteTransactionCommand,
    Money,
    ProviderObservation,
    ProviderPhase,
    TransactionView,
)
from ai_commerce_gateway.contracts.provider import ProviderService
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.core.ids import EntityPrefix, new_id
from ai_commerce_gateway.domain.enums import (
    ActorType,
    MerchantDecisionValue,
    ProviderName,
    TransactionState,
)
from ai_commerce_gateway.domain.execution import (
    EXECUTE_TRANSACTION_OPERATION,
    IdempotencyRecord,
    PaymentAttempt,
    execution_request_fingerprint,
    provider_request_fingerprint,
    response_fingerprint,
)
from ai_commerce_gateway.domain.proposal_gates import (
    BuyerAuthorization,
    MerchantDecision,
    MerchantPolicySnapshot,
    PurchaseProposal,
    TrustedProductSnapshot,
    require_current_product,
)
from ai_commerce_gateway.domain.transactions import Transaction

Clock = Callable[[], datetime]
IdFactory = Callable[[EntityPrefix], str]


class ExecutionRepository(Protocol):
    def get_idempotency(
        self, *, actor_id: str, operation: str, idempotency_key: str
    ) -> IdempotencyRecord | None: ...

    def claim_idempotency(self, record: IdempotencyRecord) -> tuple[IdempotencyRecord, bool]: ...

    def save_idempotency_result(
        self,
        record_id: str,
        *,
        resource_type: str,
        resource_id: str,
        response_code: int | None,
        response_body_hash: str | None,
    ) -> None: ...

    def lock_transaction(self, transaction_id: str) -> Transaction | None: ...
    def get_transaction(self, transaction_id: str) -> Transaction | None: ...
    def get_proposal(self, proposal_id: str) -> PurchaseProposal | None: ...
    def get_authorization(self, authorization_id: str) -> BuyerAuthorization | None: ...
    def get_merchant_decision(self, decision_id: str) -> MerchantDecision | None: ...
    def get_active_policy(self, merchant_id: str) -> MerchantPolicySnapshot | None: ...
    def get_product(self, product_id: str) -> TrustedProductSnapshot | None: ...
    def get_payment_attempt(self, transaction_id: str) -> PaymentAttempt | None: ...
    def add_payment_attempt(self, attempt: PaymentAttempt) -> None: ...

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


class ExecutionUnitOfWork(Protocol):
    repository: ExecutionRepository

    def __enter__(self) -> "ExecutionUnitOfWork": ...
    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


UnitOfWorkFactory = Callable[[], ExecutionUnitOfWork]


class TransactionExecutionApplicationService:
    """Dispatch one durable attempt through the provisional provider abstraction."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        provider_service: ProviderService,
        *,
        provider: ProviderName,
        clock: Clock | None = None,
        id_factory: IdFactory = new_id,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._provider_service = provider_service
        self._provider = provider
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory

    def execute(self, command: ExecuteTransactionCommand, actor: ActorContext) -> TransactionView:
        _require_buyer_actor(actor)
        request_hash = execution_request_fingerprint(
            actor_id=actor.actor_id,
            transaction_id=command.transaction_id,
        )
        idempotency = IdempotencyRecord(
            id=self._id_factory("idem"),
            actor_id=actor.actor_id,
            operation=EXECUTE_TRANSACTION_OPERATION,
            idempotency_key=command.idempotency_key,
            request_fingerprint=request_hash,
            resource_type=None,
            resource_id=None,
            response_code=None,
            response_body_hash=None,
            created_at=self._clock(),
        )

        with self._unit_of_work_factory() as unit_of_work:
            repository = unit_of_work.repository
            existing = repository.get_idempotency(
                actor_id=idempotency.actor_id,
                operation=idempotency.operation,
                idempotency_key=idempotency.idempotency_key,
            )
            if existing is not None:
                existing.require_same_request(request_hash)
                return self._replay(repository, existing, actor)

            transaction = _get_locked_transaction(repository, command.transaction_id)
            _require_transaction_owner(actor, transaction)
            claimed, is_new = repository.claim_idempotency(idempotency)
            claimed.require_same_request(request_hash)
            if not is_new:
                return self._replay(repository, claimed, actor)
            if transaction.state is not TransactionState.READY:
                view = _transaction_view(
                    transaction, repository.get_payment_attempt(transaction.id)
                )
                _save_success(repository, claimed.id, view)
                return view

            _revalidate_execution(repository, transaction, now=self._clock())
            existing_attempt = repository.get_payment_attempt(transaction.id)
            if existing_attempt is not None:
                raise AppError(
                    ErrorCode.INTERNAL_ERROR,
                    "A READY transaction already has a provider attempt.",
                    status_code=500,
                )
            attempt = PaymentAttempt(
                id=self._id_factory("pay"),
                transaction_id=transaction.id,
                attempt_number=1,
                provider=self._provider,
                provider_request_fingerprint=provider_request_fingerprint(
                    transaction, self._provider
                ),
                provider_order_id=None,
                provider_payment_id=None,
                provider_order_state=None,
                provider_payment_state=None,
                capture_state=None,
                last_verified_at=None,
                created_at=self._clock(),
                updated_at=self._clock(),
            )
            repository.add_payment_attempt(attempt)
            transaction = repository.transition(
                transaction.id,
                TransactionState.EXECUTING,
                actor_type=actor.actor_type,
                actor_id=actor.actor_id,
                reason_code="PROVIDER_ATTEMPT_CREATED",
                correlation_id=actor.correlation_id,
                metadata={
                    **_audit_scope(transaction),
                    "attempt_id": attempt.id,
                    "attempt_number": attempt.attempt_number,
                    "provider": attempt.provider.value,
                },
            )
            repository.save_idempotency_result(
                claimed.id,
                resource_type="transaction",
                resource_id=transaction.id,
                response_code=None,
                response_body_hash=None,
            )

        provider_command = CreateProviderOrderCommand(
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
            observation = self._provider_service.create_order(provider_command)
        except Exception as exc:
            self._record_unknown(
                transaction.id,
                claimed.id,
                actor,
                reason_code="PROVIDER_DISPATCH_UNCERTAIN",
            )
            raise _unknown_outcome_error(transaction.id) from exc

        if observation.provider is not self._provider or not observation.provider_order_id:
            self._record_unknown(
                transaction.id,
                claimed.id,
                actor,
                reason_code="PROVIDER_OBSERVATION_INCOMPLETE",
                observation=observation,
            )
            raise _unknown_outcome_error(transaction.id)

        with self._unit_of_work_factory() as unit_of_work:
            repository = unit_of_work.repository
            current = _get_locked_transaction(repository, transaction.id)
            _require_transaction_owner(actor, current)
            stored_attempt: PaymentAttempt | None
            if current.state is TransactionState.EXECUTING:
                stored_attempt = repository.save_provider_observation(attempt.id, observation)
                current = repository.transition(
                    current.id,
                    TransactionState.PAYMENT_PENDING,
                    actor_type=ActorType.SYSTEM,
                    actor_id=None,
                    reason_code="PROVIDER_ORDER_CREATED",
                    correlation_id=actor.correlation_id,
                    provider_reference_redacted=_redact_provider_reference(
                        observation.provider_order_id
                    ),
                    metadata={
                        **_audit_scope(current),
                        "attempt_id": attempt.id,
                        "provider": observation.provider.value,
                        "observation_source": observation.observation_source,
                        "authenticity_verified": observation.authenticity_verified,
                    },
                )
            else:
                stored_attempt = repository.get_payment_attempt(current.id)
            view = _transaction_view(current, stored_attempt)
            _save_success(repository, claimed.id, view)
            return view

    def _replay(
        self,
        repository: ExecutionRepository,
        idempotency: IdempotencyRecord,
        actor: ActorContext,
    ) -> TransactionView:
        if idempotency.resource_id is None:
            raise AppError(
                ErrorCode.INTERNAL_ERROR,
                "Idempotency claim has no bound transaction.",
                status_code=500,
            )
        transaction = repository.get_transaction(idempotency.resource_id)
        if transaction is None:
            raise AppError(
                ErrorCode.INTERNAL_ERROR,
                "Idempotency claim references a missing transaction.",
                status_code=500,
            )
        _require_transaction_owner(actor, transaction)
        if idempotency.response_code == 503:
            raise _unknown_outcome_error(transaction.id)
        return _transaction_view(transaction, repository.get_payment_attempt(transaction.id))

    def _record_unknown(
        self,
        transaction_id: str,
        idempotency_id: str,
        actor: ActorContext,
        *,
        reason_code: str,
        observation: ProviderObservation | None = None,
    ) -> None:
        with self._unit_of_work_factory() as unit_of_work:
            repository = unit_of_work.repository
            current = _get_locked_transaction(repository, transaction_id)
            attempt = repository.get_payment_attempt(transaction_id)
            if observation is not None and attempt is not None:
                attempt = repository.save_provider_observation(attempt.id, observation)
            if current.state is TransactionState.EXECUTING:
                current = repository.transition(
                    current.id,
                    TransactionState.UNKNOWN,
                    actor_type=ActorType.SYSTEM,
                    actor_id=None,
                    reason_code=reason_code,
                    correlation_id=actor.correlation_id,
                    provider_reference_redacted=_redact_provider_reference(
                        observation.provider_order_id if observation is not None else None
                    ),
                    metadata={
                        **_audit_scope(current),
                        "attempt_id": attempt.id if attempt is not None else None,
                        "provider": self._provider.value,
                    },
                )
            error_body = json.dumps(
                {
                    "code": ErrorCode.PROVIDER_OUTCOME_UNKNOWN.value,
                    "transaction_id": current.id,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            repository.save_idempotency_result(
                idempotency_id,
                resource_type="transaction",
                resource_id=current.id,
                response_code=503,
                response_body_hash=response_fingerprint(error_body),
            )


def _get_locked_transaction(repository: ExecutionRepository, transaction_id: str) -> Transaction:
    transaction = repository.lock_transaction(transaction_id)
    if transaction is None:
        raise AppError(ErrorCode.NOT_FOUND, "Transaction was not found.", status_code=404)
    return transaction


def _revalidate_execution(
    repository: ExecutionRepository, transaction: Transaction, *, now: datetime
) -> None:
    proposal = repository.get_proposal(transaction.proposal_id)
    if proposal is None:
        raise AppError(ErrorCode.PROPOSAL_STALE, "Purchase proposal disappeared.", status_code=409)
    if (
        proposal.buyer_id != transaction.buyer_id
        or proposal.merchant_id != transaction.merchant_id
        or proposal.total_minor != transaction.amount_minor
        or proposal.currency != transaction.currency
    ):
        raise AppError(
            ErrorCode.PROPOSAL_STALE,
            "Transaction no longer matches its proposal snapshot.",
            status_code=409,
        )
    if transaction.buyer_authorization_id is None:
        raise AppError(
            ErrorCode.AUTHORIZATION_REQUIRED,
            "Transaction has no buyer authorization.",
            status_code=409,
        )
    authorization = repository.get_authorization(transaction.buyer_authorization_id)
    if authorization is None:
        raise AppError(
            ErrorCode.AUTHORIZATION_REQUIRED,
            "Buyer authorization was not found.",
            status_code=409,
        )
    authorization.require_matches(proposal, now=now)
    if transaction.merchant_decision_id is None:
        raise AppError(
            ErrorCode.MERCHANT_REVIEW_REQUIRED,
            "Transaction has no merchant acceptance.",
            status_code=409,
        )
    decision = repository.get_merchant_decision(transaction.merchant_decision_id)
    if decision is None:
        raise AppError(
            ErrorCode.MERCHANT_REVIEW_REQUIRED,
            "Merchant acceptance was not found.",
            status_code=409,
        )
    decision.require_matches(proposal, now=now)
    policy = repository.get_active_policy(transaction.merchant_id)
    if (
        policy is None
        or not decision.is_current_for(policy)
        or decision.decision is not MerchantDecisionValue.ALLOW
    ):
        raise AppError(
            ErrorCode.MERCHANT_REVIEW_REQUIRED,
            "A current merchant acceptance is required.",
            status_code=409,
        )
    product = repository.get_product(proposal.product_id)
    if product is None:
        raise AppError(
            ErrorCode.PROPOSAL_STALE,
            "Proposal product no longer exists.",
            status_code=409,
        )
    require_current_product(proposal, product)


def _require_buyer_actor(actor: ActorContext) -> None:
    if actor.actor_type is not ActorType.BUYER:
        raise AppError(ErrorCode.FORBIDDEN, "A buyer identity is required.", status_code=403)


def _require_transaction_owner(actor: ActorContext, transaction: Transaction) -> None:
    if actor.actor_id != transaction.buyer_id:
        raise AppError(ErrorCode.FORBIDDEN, "Buyer does not own this transaction.", status_code=403)


def _transaction_view(transaction: Transaction, attempt: PaymentAttempt | None) -> TransactionView:
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


def _save_success(
    repository: ExecutionRepository, idempotency_id: str, view: TransactionView
) -> None:
    response_body = view.model_dump_json()
    repository.save_idempotency_result(
        idempotency_id,
        resource_type="transaction",
        resource_id=view.id,
        response_code=200,
        response_body_hash=response_fingerprint(response_body),
    )


def _unknown_outcome_error(transaction_id: str) -> AppError:
    return AppError(
        ErrorCode.PROVIDER_OUTCOME_UNKNOWN,
        "Provider outcome is unknown; reconciliation is required before another attempt.",
        status_code=503,
        details={"transaction_id": transaction_id},
    )


def _redact_provider_reference(reference: str | None) -> str | None:
    if not reference:
        return None
    return f"...{reference[-4:]}"


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
