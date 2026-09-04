import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_commerce_gateway.application.reconciliation import (
    TransactionReconciliationApplicationService,
)
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    Money,
    ReconcileTransactionCommand,
)
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ActorType, ProviderName, TransactionState
from ai_commerce_gateway.domain.provider_verification import ProviderEvidence
from ai_commerce_gateway.infrastructure.database import models
from ai_commerce_gateway.infrastructure.database.execution import (
    SqlAlchemyExecutionUnitOfWork,
)

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


@pytest.fixture
def db_engine():
    # Use in-memory sqlite or actual db url if needed
    url = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
    engine = create_engine(url)
    models.Base.metadata.create_all(engine)
    yield engine
    models.Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
def seed_data(session_factory) -> str:
    transaction_id = "txn_recon_123"
    with session_factory() as session:
        session.add(models.Merchant(id="merch_1", name="Merch"))
        session.add(models.Buyer(id="buyer_1", external_identity="ext_1"))
        session.add(
            models.Product(
                id="prod_1",
                merchant_id="merch_1",
                sku="PROD1",
                title="Product 1",
                description="desc",
                price_minor=100,
                currency="INR",
                available_quantity=10,
            )
        )
        session.add(
            models.PurchaseProposal(
                id="prop_1",
                buyer_id="buyer_1",
                merchant_id="merch_1",
                product_id="prod_1",
                product_version=1,
                quantity=1,
                unit_price_minor=100,
                total_minor=100,
                currency="INR",
                proposal_hash="hash",
                expires_at=NOW,
            )
        )
        session.add(
            models.Transaction(
                id=transaction_id,
                proposal_id="prop_1",
                merchant_id="merch_1",
                buyer_id="buyer_1",
                amount_minor=100,
                currency="INR",
                state=TransactionState.EXECUTING.value,
            )
        )
        session.add(
            models.PaymentAttempt(
                id="pay_1",
                transaction_id=transaction_id,
                attempt_number=1,
                provider=ProviderName.RAZORPAY.value,
                provider_request_fingerprint="hash",
                provider_order_id="order_test_123",
                provider_order_state="created",
            )
        )
        session.commit()
    return transaction_id


class FakeProviderAdapter:
    def __init__(
        self,
        order_observation=None,
        payment_observation=None,
        receipt_observation=None,
        error=None,
    ):
        self.order_observation = order_observation
        self.payment_observation = payment_observation
        self.receipt_observation = receipt_observation
        self.error = error
        self.receipt_lookups = 0
        self.order_lookups = 0

    def lookup_order_by_receipt(self, command):
        self.receipt_lookups += 1
        if self.error:
            raise self.error
        return self.receipt_observation

    def lookup_order(self, command):
        self.order_lookups += 1
        if self.error:
            raise self.error
        return self.order_observation

    def lookup_payment(self, command):
        if self.error:
            raise self.error
        return self.payment_observation


def test_reconciliation_integration_executing_to_pending(session_factory, seed_data) -> None:
    provider = FakeProviderAdapter(
        order_observation=ProviderEvidence(
            provider=ProviderName.RAZORPAY,
            provider_amount=Money(amount_minor=100, currency="INR"),
            provider_order_id="order_test_123",
            provider_order_state="created",
            authenticity_verified=True,
            observed_at=NOW,
            observation_source="lookup",
        )
    )
    service = TransactionReconciliationApplicationService(
        unit_of_work_factory=lambda: SqlAlchemyExecutionUnitOfWork(session_factory),
        provider_service=provider,
    )
    result = service.reconcile(
        ReconcileTransactionCommand(transaction_id=seed_data, idempotency_key="k1"),
        ActorContext(actor_id="sys", actor_type=ActorType.SYSTEM, correlation_id="c1"),
    )
    assert result.state == TransactionState.PAYMENT_PENDING





def test_reconciliation_integration_unknown_to_succeeded(session_factory, seed_data) -> None:
    # First set it to UNKNOWN and add a payment ID to the attempt
    with session_factory() as session:
        txn = session.get(models.Transaction, seed_data)
        txn.state = TransactionState.UNKNOWN.value

        attempt = session.query(models.PaymentAttempt).filter_by(transaction_id=seed_data).first()
        attempt.provider_payment_id = "pay_test_123"
        session.commit()

    provider = FakeProviderAdapter(
        order_observation=ProviderEvidence(
            provider=ProviderName.RAZORPAY,
            provider_amount=Money(amount_minor=100, currency="INR"),
            provider_order_id="order_test_123",
            provider_order_state="paid",
            authenticity_verified=True,
            observed_at=NOW,
            observation_source="lookup",
        ),
        payment_observation=ProviderEvidence(
            provider=ProviderName.RAZORPAY,
            provider_amount=Money(amount_minor=100, currency="INR"),
            provider_order_id="order_test_123",
            provider_payment_id="pay_test_123",
            provider_payment_state="captured",
            capture_state="captured",
            authenticity_verified=True,
            observed_at=NOW,
            observation_source="lookup",
        ),
    )
    service = TransactionReconciliationApplicationService(
        unit_of_work_factory=lambda: SqlAlchemyExecutionUnitOfWork(session_factory),
        provider_service=provider,
    )
    result = service.reconcile(
        ReconcileTransactionCommand(transaction_id=seed_data, idempotency_key="k2"),
        ActorContext(actor_id="sys", actor_type=ActorType.SYSTEM, correlation_id="c2"),
    )
    assert result.state == TransactionState.SUCCEEDED


def test_reconciliation_integration_no_order(session_factory, seed_data) -> None:
    provider = FakeProviderAdapter(error=AppError(ErrorCode.PROVIDER_ERROR, "Not found"))
    service = TransactionReconciliationApplicationService(
        unit_of_work_factory=lambda: SqlAlchemyExecutionUnitOfWork(session_factory),
        provider_service=provider,
    )
    result = service.reconcile(
        ReconcileTransactionCommand(transaction_id=seed_data, idempotency_key="k3"),
        ActorContext(actor_id="sys", actor_type=ActorType.SYSTEM, correlation_id="c3"),
    )
    assert result.state == TransactionState.UNKNOWN


def test_reconciliation_integration_missing_attempt(session_factory, seed_data) -> None:
    with session_factory() as session:
        session.query(models.PaymentAttempt).delete()
        session.commit()

    service = TransactionReconciliationApplicationService(
        unit_of_work_factory=lambda: SqlAlchemyExecutionUnitOfWork(session_factory),
        provider_service=FakeProviderAdapter(),
    )
    result = service.reconcile(
        ReconcileTransactionCommand(transaction_id=seed_data, idempotency_key="k4"),
        ActorContext(actor_id="sys", actor_type=ActorType.SYSTEM, correlation_id="c4"),
    )
    assert result.state == TransactionState.UNKNOWN


def test_reconciliation_recovers_lost_response_by_receipt_without_redispatch(
    session_factory, seed_data
) -> None:
    with session_factory() as session:
        transaction = session.get(models.Transaction, seed_data)
        transaction.state = TransactionState.UNKNOWN.value
        attempt = session.query(models.PaymentAttempt).filter_by(transaction_id=seed_data).one()
        attempt.provider_order_id = None
        attempt.provider_order_state = None
        session.commit()

    recovered = ProviderEvidence(
        provider=ProviderName.RAZORPAY,
        provider_amount=Money(amount_minor=100, currency="INR"),
        provider_order_id="order_recovered_123",
        provider_order_state="created",
        authenticity_verified=True,
        observed_at=NOW,
        observation_source="receipt_lookup",
    )
    provider = FakeProviderAdapter(
        receipt_observation=recovered,
        order_observation=recovered,
    )
    service = TransactionReconciliationApplicationService(
        unit_of_work_factory=lambda: SqlAlchemyExecutionUnitOfWork(session_factory),
        provider_service=provider,
    )

    result = service.reconcile(
        ReconcileTransactionCommand(transaction_id=seed_data, idempotency_key="k5"),
        ActorContext(actor_id="sys", actor_type=ActorType.SYSTEM, correlation_id="c5"),
    )

    assert result.state is TransactionState.PAYMENT_PENDING
    assert provider.receipt_lookups == 1
    assert provider.order_lookups == 1
    assert not hasattr(provider, "create_order")
    with session_factory() as session:
        attempt = session.query(models.PaymentAttempt).filter_by(transaction_id=seed_data).one()
        events = list(
            session.query(models.TransactionEvent)
            .filter_by(transaction_id=seed_data)
            .order_by(models.TransactionEvent.created_at)
        )
        assert attempt.provider_order_id == "order_recovered_123"
        assert events[-1].metadata_json["recovery_method"] == "transaction_receipt"
        assert events[-1].provider_reference_redacted == "..._123"
