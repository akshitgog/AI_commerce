from dataclasses import replace
from datetime import UTC, datetime

import pytest

from ai_commerce_gateway.application.reconciliation import (
    TransactionReconciliationApplicationService,
)
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    ProviderLookupCommand,
    ProviderObservation,
    ReconcileTransactionCommand,
)
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ActorType, ProviderName, TransactionState
from ai_commerce_gateway.domain.execution import PaymentAttempt
from ai_commerce_gateway.domain.transactions import Transaction

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


class FakeProvider:
    def __init__(
        self,
        order_observation: ProviderObservation | None = None,
        payment_observation: ProviderObservation | None = None,
        error: Exception | None = None,
    ):
        self.order_observation = order_observation
        self.payment_observation = payment_observation
        self.error = error
        self.order_lookups: list[str] = []
        self.payment_lookups: list[tuple[str, str]] = []

    def lookup_order(self, command: ProviderLookupCommand) -> ProviderObservation:
        if self.error:
            raise self.error
        if command.provider_order_id is None:
            raise ValueError("missing order id")
        self.order_lookups.append(command.provider_order_id)
        if self.order_observation is None:
            raise RuntimeError("no mock data")
        return self.order_observation

    def lookup_payment(self, command: ProviderLookupCommand) -> ProviderObservation:
        if self.error:
            raise self.error
        if command.provider_payment_id is None or command.provider_order_id is None:
            raise ValueError("missing payment ids")
        self.payment_lookups.append((command.provider_order_id, command.provider_payment_id))
        if self.payment_observation is None:
            raise RuntimeError("no mock data")
        return self.payment_observation


class FakeRepository:
    def __init__(self, transaction: Transaction, attempt: PaymentAttempt | None = None):
        self._transaction = transaction
        self._attempt = attempt
        self.transitions: list[tuple[str, TransactionState]] = []

    def lock_transaction(self, transaction_id: str) -> Transaction | None:
        if transaction_id == self._transaction.id:
            return self._transaction
        return None

    def get_payment_attempt(self, transaction_id: str) -> PaymentAttempt | None:
        if transaction_id == self._transaction.id:
            return self._attempt
        return None

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
    ) -> Transaction:
        self.transitions.append((transaction_id, new_state))
        self._transaction = Transaction(
            id=self._transaction.id,
            proposal_id=self._transaction.proposal_id,
            buyer_authorization_id=self._transaction.buyer_authorization_id,
            merchant_decision_id=self._transaction.merchant_decision_id,
            merchant_id=self._transaction.merchant_id,
            buyer_id=self._transaction.buyer_id,
            amount_minor=self._transaction.amount_minor,
            currency=self._transaction.currency,
            state=new_state,
            created_at=self._transaction.created_at,
            updated_at=NOW,
        )
        return self._transaction


class FakeUoW:
    def __init__(self, repository: FakeRepository):
        self.repository = repository

    def __enter__(self) -> "FakeUoW":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        pass


@pytest.fixture
def transaction() -> Transaction:
    return Transaction(
        id="txn_123",
        proposal_id="prop_123",
        buyer_authorization_id="auth_123",
        merchant_decision_id="dec_123",
        merchant_id="merch_123",
        buyer_id="buyer_123",
        amount_minor=1000,
        currency="INR",
        state=TransactionState.UNKNOWN,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def attempt() -> PaymentAttempt:
    return PaymentAttempt(
        id="pay_123",
        transaction_id="txn_123",
        attempt_number=1,
        provider=ProviderName.RAZORPAY,
        provider_request_fingerprint="sha256:123",
        provider_order_id="order_123",
        provider_payment_id="pay_123",
        provider_order_state="created",
        provider_payment_state=None,
        capture_state=None,
        last_verified_at=None,
        created_at=NOW,
        updated_at=NOW,
    )


def test_reconcile_no_attempt_fails_fast(transaction: Transaction) -> None:
    repository = FakeRepository(transaction, None)
    service = TransactionReconciliationApplicationService(
        lambda: FakeUoW(repository), FakeProvider()
    )
    result = service.reconcile(
        ReconcileTransactionCommand(transaction_id="txn_123", idempotency_key="key_1"),
        ActorContext(actor_id="sys", actor_type=ActorType.SYSTEM, correlation_id="c1"),
    )
    assert result.state == TransactionState.FAILED
    assert repository.transitions == [
        ("txn_123", TransactionState.RECONCILING),
        ("txn_123", TransactionState.FAILED),
    ]





def test_reconcile_ignores_ready_transactions(
    transaction: Transaction, attempt: PaymentAttempt
) -> None:
    transaction = replace(transaction, state=TransactionState.SUCCEEDED)
    repository = FakeRepository(transaction, attempt)
    service = TransactionReconciliationApplicationService(
        lambda: FakeUoW(repository), FakeProvider()
    )
    result = service.reconcile(
        ReconcileTransactionCommand(transaction_id="txn_123", idempotency_key="key_1"),
        ActorContext(actor_id="sys", actor_type=ActorType.SYSTEM, correlation_id="c1"),
    )
    assert result.state == TransactionState.SUCCEEDED
    assert repository.transitions == []


def test_reconcile_paid_order_and_captured_payment(
    transaction: Transaction, attempt: PaymentAttempt
) -> None:
    provider = FakeProvider(
        order_observation=ProviderObservation(
            provider=ProviderName.RAZORPAY,
            provider_order_state="paid",
            authenticity_verified=True,
            observed_at=NOW,
            observation_source="lookup",
        ),
        payment_observation=ProviderObservation(
            provider=ProviderName.RAZORPAY,
            provider_payment_state="captured",
            capture_state="captured",
            authenticity_verified=True,
            observed_at=NOW,
            observation_source="lookup",
        ),
    )
    repository = FakeRepository(transaction, attempt)
    service = TransactionReconciliationApplicationService(lambda: FakeUoW(repository), provider)

    result = service.reconcile(
        ReconcileTransactionCommand(transaction_id="txn_123", idempotency_key="key_1"),
        ActorContext(actor_id="sys", actor_type=ActorType.SYSTEM, correlation_id="c1"),
    )
    assert result.state == TransactionState.SUCCEEDED
    assert repository.transitions == [
        ("txn_123", TransactionState.RECONCILING),
        ("txn_123", TransactionState.SUCCEEDED),
    ]
    assert provider.order_lookups == ["order_123"]
    assert provider.payment_lookups == [("order_123", "pay_123")]


def test_reconcile_provider_lookup_failure_stays_unknown(
    transaction: Transaction, attempt: PaymentAttempt
) -> None:
    provider = FakeProvider(error=AppError(ErrorCode.PROVIDER_ERROR, "Network error"))
    repository = FakeRepository(transaction, attempt)
    service = TransactionReconciliationApplicationService(lambda: FakeUoW(repository), provider)

    result = service.reconcile(
        ReconcileTransactionCommand(transaction_id="txn_123", idempotency_key="key_1"),
        ActorContext(actor_id="sys", actor_type=ActorType.SYSTEM, correlation_id="c1"),
    )
    assert result.state == TransactionState.UNKNOWN
    assert repository.transitions == [
        ("txn_123", TransactionState.RECONCILING),
        ("txn_123", TransactionState.UNKNOWN),
    ]
