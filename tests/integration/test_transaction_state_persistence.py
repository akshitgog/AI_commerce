import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.core.ids import new_id
from ai_commerce_gateway.domain.enums import ActorType, TransactionState
from ai_commerce_gateway.infrastructure.database.models import (
    Base,
    Buyer,
    Merchant,
    Product,
    PurchaseProposal,
)
from ai_commerce_gateway.infrastructure.database.models import (
    Transaction as TransactionRecord,
)
from ai_commerce_gateway.infrastructure.database.models import (
    TransactionEvent as TransactionEventRecord,
)
from ai_commerce_gateway.infrastructure.database.transactions import (
    SqlAlchemyTransactionStateRepository,
)

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


@contextmanager
def rollback_session(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


def seed_ready_transaction(session: Session) -> str:
    suffix = new_id("txn").removeprefix("txn_")
    merchant_id = f"mer_{suffix}"
    product_id = f"prod_{suffix}"
    buyer_id = f"buy_{suffix}"
    proposal_id = f"prop_{suffix}"
    transaction_id = f"txn_{suffix}"
    session.add_all(
        [
            Merchant(id=merchant_id, name="Test Merchant", status="ACTIVE"),
            Product(
                id=product_id,
                merchant_id=merchant_id,
                sku=f"sku-{suffix}",
                title="Test Product",
                description="Persistence fixture",
                category=None,
                price_minor=50_000,
                currency="INR",
                available_quantity=1,
                status="PUBLISHED",
                version=1,
            ),
            Buyer(id=buyer_id, external_identity=f"buyer-{suffix}", status="ACTIVE"),
            PurchaseProposal(
                id=proposal_id,
                buyer_id=buyer_id,
                merchant_id=merchant_id,
                product_id=product_id,
                product_version=1,
                quantity=1,
                unit_price_minor=50_000,
                total_minor=50_000,
                currency="INR",
                proposal_hash=f"sha256:{suffix}",
                status="PROPOSED",
                expires_at=NOW + timedelta(minutes=10),
            ),
        ]
    )
    session.flush()
    session.add(
        TransactionRecord(
            id=transaction_id,
            proposal_id=proposal_id,
            buyer_authorization_id=None,
            merchant_decision_id=None,
            merchant_id=merchant_id,
            buyer_id=buyer_id,
            amount_minor=50_000,
            currency="INR",
            state=TransactionState.READY.value,
        )
    )
    session.flush()
    return transaction_id


def assert_atomic_transition_behavior(session: Session) -> None:
    transaction_id = seed_ready_transaction(session)
    event_id = new_id("tevt")
    repository = SqlAlchemyTransactionStateRepository(
        session,
        event_id_factory=lambda: event_id,
        clock=lambda: NOW,
    )
    result = repository.transition(
        transaction_id,
        TransactionState.EXECUTING,
        actor_type=ActorType.BUYER,
        actor_id="buy_actor",
        reason_code="EXECUTION_REQUESTED",
        correlation_id="corr_test",
        metadata={
            "source": "test",
            "gates": {"buyer": "approved"},
            "checks": ["buyer", "merchant"],
        },
    )
    session.expire_all()

    persisted_transaction = session.get(TransactionRecord, transaction_id)
    persisted_event = session.get(TransactionEventRecord, event_id)
    assert persisted_transaction is not None
    assert persisted_transaction.state == TransactionState.EXECUTING.value
    assert persisted_event is not None
    assert persisted_event.previous_state == TransactionState.READY.value
    assert persisted_event.new_state == TransactionState.EXECUTING.value
    assert persisted_event.reason_code == "EXECUTION_REQUESTED"
    assert persisted_event.correlation_id == "corr_test"
    assert persisted_event.metadata_json == {
        "source": "test",
        "gates": {"buyer": "approved"},
        "checks": ["buyer", "merchant"],
    }
    assert result.event.id == event_id
    session.expunge(persisted_event)

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            repository.transition(
                transaction_id,
                TransactionState.PAYMENT_PENDING,
                actor_type=ActorType.SYSTEM,
                actor_id=None,
                reason_code="PROVIDER_ORDER_CREATED",
                correlation_id="corr_test",
            )

    session.expire_all()
    persisted_transaction = session.get(TransactionRecord, transaction_id)
    event_count = session.scalar(
        select(func.count())
        .select_from(TransactionEventRecord)
        .where(TransactionEventRecord.transaction_id == transaction_id)
    )
    assert persisted_transaction is not None
    assert persisted_transaction.state == TransactionState.EXECUTING.value
    assert event_count == 1


def test_state_update_and_event_append_are_atomic_in_sqlite() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with rollback_session(engine) as session:
            assert_atomic_transition_behavior(session)
    finally:
        engine.dispose()


@pytest.mark.integration
def test_state_update_and_event_append_are_atomic_in_postgresql_when_configured() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with rollback_session(engine) as session:
            assert_atomic_transition_behavior(session)
    finally:
        engine.dispose()


def test_missing_transaction_is_rejected_without_an_event() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with rollback_session(engine) as session:
            repository = SqlAlchemyTransactionStateRepository(session, clock=lambda: NOW)
            with pytest.raises(AppError) as error:
                repository.transition(
                    "txn_missing",
                    TransactionState.EXECUTING,
                    actor_type=ActorType.SYSTEM,
                    actor_id=None,
                    reason_code="EXECUTION_REQUESTED",
                    correlation_id="corr_test",
                )
            assert error.value.code is ErrorCode.NOT_FOUND
            assert session.scalar(select(func.count()).select_from(TransactionEventRecord)) == 0
    finally:
        engine.dispose()
