from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

from ai_commerce_gateway.contracts.models import (
    HandleWebhookCommand,
    Money,
    ProviderLookupCommand,
    ProviderObservation,
    ProviderPhase,
    TransactionView,
    VerifyCheckoutCommand,
)
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.core.ids import EntityPrefix, new_id
from ai_commerce_gateway.domain.enums import ActorType, ProviderName, TransactionState
from ai_commerce_gateway.domain.execution import PaymentAttempt
from ai_commerce_gateway.domain.provider_verification import (
    ProviderEvidence,
    ProviderWebhookReceipt,
    WebhookProcessingResult,
    webhook_payload_hash,
)
from ai_commerce_gateway.domain.transactions import Transaction

Clock = Callable[[], datetime]
IdFactory = Callable[[EntityPrefix], str]


class VerificationRepository(Protocol):
    def lock_transaction(self, transaction_id: str) -> Transaction | None: ...
    def get_payment_attempt(self, transaction_id: str) -> PaymentAttempt | None: ...
    def find_payment_attempt(
        self,
        *,
        provider_order_id: str | None,
        provider_payment_id: str | None,
    ) -> PaymentAttempt | None: ...
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
    def claim_webhook(
        self, receipt: ProviderWebhookReceipt
    ) -> tuple[ProviderWebhookReceipt, bool]: ...
    def update_webhook(
        self,
        receipt_id: str,
        *,
        transaction_id: str | None,
        processing_status: str,
        processed_at: datetime | None,
    ) -> ProviderWebhookReceipt: ...


class VerificationUnitOfWork(Protocol):
    repository: VerificationRepository

    def __enter__(self) -> "VerificationUnitOfWork": ...
    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


UnitOfWorkFactory = Callable[[], VerificationUnitOfWork]


class ProviderVerificationPort(Protocol):
    def verify_checkout(self, command: VerifyCheckoutCommand) -> ProviderEvidence: ...
    def handle_webhook(self, command: HandleWebhookCommand) -> ProviderEvidence: ...
    def lookup_order(self, command: ProviderLookupCommand) -> ProviderEvidence: ...
    def lookup_payment(self, command: ProviderLookupCommand) -> ProviderEvidence: ...


class ProviderVerificationApplicationService:
    """Verify provider evidence and apply only state-machine-approved results."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        provider_service: ProviderVerificationPort,
        *,
        provider: ProviderName = ProviderName.RAZORPAY,
        clock: Clock | None = None,
        id_factory: IdFactory = new_id,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._provider_service = provider_service
        self._provider = provider
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory

    def verify_checkout(
        self, command: VerifyCheckoutCommand, *, correlation_id: str
    ) -> TransactionView:
        with self._unit_of_work_factory() as unit_of_work:
            transaction, attempt = _load_verifiable_transaction(
                unit_of_work.repository, command.transaction_id
            )
            _require_expected_references(
                attempt,
                provider_order_id=command.provider_order_id,
                provider_payment_id=command.provider_payment_id,
            )
            already_succeeded = transaction.state is TransactionState.SUCCEEDED

        signature = self._provider_service.verify_checkout(command)
        if not signature.authenticity_verified:
            raise _provider_error("Checkout authenticity was not verified.")
        if already_succeeded:
            return _transaction_view(transaction, attempt)
        payment = self._provider_service.lookup_payment(
            ProviderLookupCommand(
                provider_order_id=attempt.provider_order_id,
                provider_payment_id=command.provider_payment_id,
            )
        )
        order = self._provider_service.lookup_order(
            ProviderLookupCommand(provider_order_id=attempt.provider_order_id)
        )
        observation = _combine_observations(
            attempt,
            signature,
            payment,
            order,
            source="checkout_signature_and_provider_lookup",
            expected_amount=Money(
                amount_minor=transaction.amount_minor,
                currency=transaction.currency,
            ),
        )
        return self._apply_observation(
            transaction.id,
            observation,
            correlation_id=correlation_id,
            reason_prefix="CHECKOUT",
        )

    def handle_webhook(
        self,
        command: HandleWebhookCommand,
        *,
        provider_event_id: str,
        correlation_id: str,
    ) -> WebhookProcessingResult:
        if not provider_event_id.strip() or len(provider_event_id) > 255:
            raise _provider_error("Webhook event identifier is invalid.")
        observation = self._provider_service.handle_webhook(command)
        if not observation.authenticity_verified:
            raise _provider_error("Webhook authenticity was not verified.")
        receipt = ProviderWebhookReceipt(
            id=self._id_factory("pwh"),
            provider=self._provider,
            provider_event_id=provider_event_id,
            payload_hash=webhook_payload_hash(command.raw_body),
            transaction_id=None,
            processing_status="RECEIVED",
            received_at=self._clock(),
            processed_at=None,
        )

        with self._unit_of_work_factory() as unit_of_work:
            repository = unit_of_work.repository
            stored, is_new = repository.claim_webhook(receipt)
            was_duplicate = not is_new
            if stored.payload_hash != receipt.payload_hash:
                raise _provider_error("Webhook event identifier was reused with another payload.")
            if not is_new and stored.processing_status != "RECEIVED":
                return WebhookProcessingResult(
                    provider_event_id=stored.provider_event_id,
                    processing_status=stored.processing_status,
                    duplicate=True,
                    transaction_id=stored.transaction_id,
                    transaction_state=_state_for(repository, stored.transaction_id),
                )
            if observation.provider_order_id is None:
                stored = repository.update_webhook(
                    stored.id,
                    transaction_id=None,
                    processing_status="IGNORED",
                    processed_at=self._clock(),
                )
                return _webhook_result(stored, duplicate=not is_new, state=None)
            attempt = repository.find_payment_attempt(
                provider_order_id=observation.provider_order_id,
                provider_payment_id=observation.provider_payment_id,
            )
            if attempt is None:
                stored = repository.update_webhook(
                    stored.id,
                    transaction_id=None,
                    processing_status="ORPHAN",
                    processed_at=self._clock(),
                )
                return _webhook_result(stored, duplicate=not is_new, state=None)
            repository.update_webhook(
                stored.id,
                transaction_id=attempt.transaction_id,
                processing_status="RECEIVED",
                processed_at=None,
            )
            receipt_id = stored.id

        final_observation = observation
        if observation.capture_state == "captured":
            payment = self._provider_service.lookup_payment(
                ProviderLookupCommand(
                    provider_order_id=observation.provider_order_id,
                    provider_payment_id=observation.provider_payment_id,
                )
            )
            order = self._provider_service.lookup_order(
                ProviderLookupCommand(provider_order_id=observation.provider_order_id)
            )
            final_observation = _combine_observations(
                attempt,
                observation,
                payment,
                order,
                source="verified_webhook_and_provider_lookup",
            )

        view = self._apply_observation(
            attempt.transaction_id,
            final_observation,
            correlation_id=correlation_id,
            reason_prefix="WEBHOOK",
        )
        with self._unit_of_work_factory() as unit_of_work:
            stored = unit_of_work.repository.update_webhook(
                receipt_id,
                transaction_id=attempt.transaction_id,
                processing_status="PROCESSED",
                processed_at=self._clock(),
            )
        return _webhook_result(stored, duplicate=was_duplicate, state=view.state)

    def _apply_observation(
        self,
        transaction_id: str,
        observation: ProviderEvidence,
        *,
        correlation_id: str,
        reason_prefix: str,
    ) -> TransactionView:
        with self._unit_of_work_factory() as unit_of_work:
            repository = unit_of_work.repository
            transaction, attempt = _load_verifiable_transaction(repository, transaction_id)
            _require_expected_references(
                attempt,
                provider_order_id=observation.provider_order_id,
                provider_payment_id=observation.provider_payment_id,
            )
            if transaction.state is TransactionState.SUCCEEDED:
                return _transaction_view(transaction, attempt)
            combined = _combine_observations(
                attempt,
                observation,
                source=observation.observation_source,
                expected_amount=Money(
                    amount_minor=transaction.amount_minor,
                    currency=transaction.currency,
                ),
            )
            attempt = repository.save_provider_observation(attempt.id, combined)
            if (
                transaction.state is TransactionState.PAYMENT_PENDING
                and combined.provider_payment_state != "failed"
            ):
                transaction = repository.transition(
                    transaction.id,
                    TransactionState.VERIFYING,
                    actor_type=ActorType.SYSTEM,
                    actor_id=None,
                    reason_code=f"{reason_prefix}_AUTHENTICITY_VERIFIED",
                    correlation_id=correlation_id,
                    provider_reference_redacted=_redact(combined.provider_payment_id),
                    metadata=_provider_metadata(attempt, combined),
                )
            if _is_verified_success(combined) and transaction.state is TransactionState.VERIFYING:
                transaction = repository.transition(
                    transaction.id,
                    TransactionState.SUCCEEDED,
                    actor_type=ActorType.SYSTEM,
                    actor_id=None,
                    reason_code="PROVIDER_PAYMENT_CAPTURED",
                    correlation_id=correlation_id,
                    provider_reference_redacted=_redact(combined.provider_payment_id),
                    metadata=_provider_metadata(attempt, combined),
                )
            return _transaction_view(transaction, attempt)


def _load_verifiable_transaction(
    repository: VerificationRepository, transaction_id: str
) -> tuple[Transaction, PaymentAttempt]:
    transaction = repository.lock_transaction(transaction_id)
    if transaction is None:
        raise AppError(ErrorCode.NOT_FOUND, "Transaction was not found.", status_code=404)
    if transaction.state not in {
        TransactionState.PAYMENT_PENDING,
        TransactionState.VERIFYING,
        TransactionState.SUCCEEDED,
    }:
        raise AppError(
            ErrorCode.INVALID_STATE,
            "Transaction is not awaiting provider verification.",
            status_code=409,
        )
    attempt = repository.get_payment_attempt(transaction.id)
    if attempt is None or attempt.provider_order_id is None:
        raise _provider_error("Transaction has no provider order to verify.")
    return transaction, attempt


def _require_expected_references(
    attempt: PaymentAttempt,
    *,
    provider_order_id: str | None,
    provider_payment_id: str | None,
) -> None:
    if provider_order_id is not None and provider_order_id != attempt.provider_order_id:
        raise _provider_error("Provider order does not belong to this transaction.")
    if (
        provider_payment_id is not None
        and attempt.provider_payment_id is not None
        and provider_payment_id != attempt.provider_payment_id
    ):
        raise _provider_error("Provider payment does not belong to this transaction.")


def _combine_observations(
    attempt: PaymentAttempt,
    *observations: ProviderEvidence,
    source: str,
    expected_amount: Money | None = None,
) -> ProviderEvidence:
    order_id = attempt.provider_order_id
    payment_id = attempt.provider_payment_id
    order_state = attempt.provider_order_state
    payment_state = attempt.provider_payment_state
    capture_state = attempt.capture_state
    provider_amount: Money | None = None
    observed_at = attempt.last_verified_at or attempt.updated_at
    authenticity_verified = True
    for observation in observations:
        if observation.provider is not attempt.provider:
            raise _provider_error("Provider observation came from another provider.")
        if order_id is not None and observation.provider_order_id not in {None, order_id}:
            raise _provider_error("Provider observation references another order.")
        if payment_id is not None and observation.provider_payment_id not in {None, payment_id}:
            raise _provider_error("Provider observation references another payment.")
        order_id = observation.provider_order_id or order_id
        payment_id = observation.provider_payment_id or payment_id
        order_state = observation.provider_order_state or order_state
        payment_state = observation.provider_payment_state or payment_state
        capture_state = observation.capture_state or capture_state
        if observation.provider_amount is not None:
            if provider_amount is not None and observation.provider_amount != provider_amount:
                raise _provider_error("Provider observations disagree about payment amount.")
            provider_amount = observation.provider_amount
        observed_at = max(observed_at, observation.observed_at)
        authenticity_verified = authenticity_verified and observation.authenticity_verified
    if expected_amount is not None and provider_amount != expected_amount:
        raise _provider_error("Provider payment amount does not match the transaction.")
    return ProviderEvidence(
        provider=attempt.provider,
        provider_amount=provider_amount,
        provider_order_id=order_id,
        provider_payment_id=payment_id,
        provider_order_state=order_state,
        provider_payment_state=payment_state,
        capture_state=capture_state,
        authenticity_verified=authenticity_verified,
        observed_at=observed_at,
        observation_source=source,
    )


def _is_verified_success(observation: ProviderEvidence) -> bool:
    return (
        observation.authenticity_verified
        and observation.provider_amount is not None
        and observation.provider_order_state == "paid"
        and observation.provider_payment_state == "captured"
        and observation.capture_state == "captured"
    )


def _provider_error(message: str) -> AppError:
    return AppError(ErrorCode.PROVIDER_ERROR, message, status_code=409)


def _redact(reference: str | None) -> str | None:
    return f"...{reference[-4:]}" if reference else None


def _provider_metadata(
    attempt: PaymentAttempt, observation: ProviderEvidence
) -> dict[str, str | int | bool | None]:
    return {
        "attempt_id": attempt.id,
        "attempt_number": attempt.attempt_number,
        "provider": attempt.provider.value,
        "order_state": observation.provider_order_state,
        "payment_state": observation.provider_payment_state,
        "capture_state": observation.capture_state,
        "authenticity_verified": observation.authenticity_verified,
        "observation_source": observation.observation_source,
    }


def _transaction_view(transaction: Transaction, attempt: PaymentAttempt | None) -> TransactionView:
    phase = None
    if attempt is not None:
        phase = ProviderPhase(
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
        provider_phase=phase,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
    )


def _webhook_result(
    receipt: ProviderWebhookReceipt,
    *,
    duplicate: bool,
    state: TransactionState | None,
) -> WebhookProcessingResult:
    return WebhookProcessingResult(
        provider_event_id=receipt.provider_event_id,
        processing_status=receipt.processing_status,
        duplicate=duplicate,
        transaction_id=receipt.transaction_id,
        transaction_state=state,
    )


def _state_for(
    repository: VerificationRepository, transaction_id: str | None
) -> TransactionState | None:
    if transaction_id is None:
        return None
    transaction = repository.lock_transaction(transaction_id)
    return transaction.state if transaction is not None else None
