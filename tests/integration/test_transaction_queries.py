from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_commerce_gateway.application.composition import compose_transaction_services
from ai_commerce_gateway.application.transaction_service import (
    TransactionQueryApplicationService,
)
from ai_commerce_gateway.contracts.models import ActorContext, ExecuteTransactionCommand
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ActorType, ProviderName, TransactionState
from ai_commerce_gateway.infrastructure.database import models
from ai_commerce_gateway.infrastructure.database.transaction_queries import (
    SqlAlchemyTransactionQueryUnitOfWork,
)
from ai_commerce_gateway.providers.razorpay import RazorpayAdapter

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    _seed(factory)
    yield factory
    if engine.dialect.name == "postgresql":
        from sqlalchemy import text

        with engine.begin() as conn:
            for table in reversed(models.Base.metadata.sorted_tables):
                conn.execute(text(f"TRUNCATE {table.name} RESTART IDENTITY CASCADE"))
    else:
        models.Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def service(session_factory) -> TransactionQueryApplicationService:
    return TransactionQueryApplicationService(
        lambda: SqlAlchemyTransactionQueryUnitOfWork(session_factory)
    )


def actor(
    actor_id: str,
    actor_type: ActorType,
    *,
    merchant_ids: frozenset[str] = frozenset(),
) -> ActorContext:
    return ActorContext(
        actor_id=actor_id,
        actor_type=actor_type,
        merchant_ids=merchant_ids,
        correlation_id="corr_query",
    )


def test_status_and_audit_are_visible_to_owner_and_merchant_tenant(
    service: TransactionQueryApplicationService,
) -> None:
    buyer_view = service.get_status("txn_1", actor("buyer_1", ActorType.BUYER))
    merchant_view = service.get_status(
        "txn_1",
        actor(
            "user_1",
            ActorType.MERCHANT_USER,
            merchant_ids=frozenset({"merch_1"}),
        ),
    )
    audit = service.get_audit("txn_1", actor("buyer_1", ActorType.BUYER))

    assert buyer_view == merchant_view
    assert buyer_view.amount.amount_minor == 169_900
    assert buyer_view.amount.currency == "INR"
    assert buyer_view.provider_phase is not None
    assert buyer_view.provider_phase.order_state == "created"
    assert [event.reason_code for event in audit.items[:2]] == [
        "GATES_SATISFIED",
        "PROVIDER_ATTEMPT_CREATED",
    ]
    assert audit.items[0].metadata["amount_minor"] == 169_900
    assert audit.items[0].metadata["currency"] == "INR"
    assert audit.items[0].actor_type is ActorType.BUYER
    assert audit.items[0].actor_id == "buyer_1"
    assert audit.items[0].previous_state is None
    assert audit.items[0].new_state is TransactionState.READY
    assert audit.items[0].correlation_id == "corr_000"
    assert audit.items[0].created_at.tzinfo is UTC
    assert audit.items[1].provider_reference_redacted == "...3456"
    assert "order_test_123456" not in audit.model_dump_json()


@pytest.mark.parametrize(
    "unauthorized_actor",
    [
        actor("buyer_2", ActorType.BUYER),
        actor(
            "user_2",
            ActorType.MERCHANT_USER,
            merchant_ids=frozenset({"merch_2"}),
        ),
    ],
)
def test_status_and_audit_deny_cross_tenant_access(
    service: TransactionQueryApplicationService,
    unauthorized_actor: ActorContext,
) -> None:
    with pytest.raises(AppError) as status_error:
        service.get_status("txn_1", unauthorized_actor)
    with pytest.raises(AppError) as audit_error:
        service.get_audit("txn_1", unauthorized_actor)

    assert status_error.value.code is ErrorCode.FORBIDDEN
    assert audit_error.value.code is ErrorCode.FORBIDDEN


def test_merchant_list_is_tenant_scoped(service: TransactionQueryApplicationService) -> None:
    merchant = actor(
        "user_1",
        ActorType.MERCHANT_USER,
        merchant_ids=frozenset({"merch_1"}),
    )
    page = service.list_for_merchant("merch_1", merchant)
    assert [item.id for item in page.items] == ["txn_1"]

    with pytest.raises(AppError) as error:
        service.list_for_merchant("merch_2", merchant)
    assert error.value.code is ErrorCode.FORBIDDEN

    with pytest.raises(AppError) as cursor_error:
        service.list_for_merchant("merch_1", merchant, cursor="txn_2")
    assert cursor_error.value.code is ErrorCode.VALIDATION_ERROR


def test_audit_cursor_is_stable_and_bound_to_transaction(
    service: TransactionQueryApplicationService,
) -> None:
    buyer = actor("buyer_1", ActorType.BUYER)
    first = service.get_audit("txn_1", buyer)
    assert len(first.items) == 50
    assert first.next_cursor == first.items[-1].id

    second = service.get_audit("txn_1", buyer, first.next_cursor)
    assert len(second.items) == 2
    assert second.next_cursor is None
    assert set(item.id for item in first.items).isdisjoint(item.id for item in second.items)

    with pytest.raises(AppError) as error:
        service.get_audit("txn_1", buyer, "tevt_other_transaction")
    assert error.value.code is ErrorCode.VALIDATION_ERROR


def test_missing_transaction_does_not_disclose_data(
    service: TransactionQueryApplicationService,
) -> None:
    with pytest.raises(AppError) as error:
        service.get_status("txn_missing", actor("buyer_1", ActorType.BUYER))
    assert error.value.code is ErrorCode.NOT_FOUND
    assert error.value.status_code == 404


def test_production_composition_exposes_one_complete_transaction_service(
    session_factory,
) -> None:
    provider_requests: list[httpx.Request] = []

    def provider_handler(request: httpx.Request) -> httpx.Response:
        provider_requests.append(request)
        return httpx.Response(500)

    with httpx.Client(transport=httpx.MockTransport(provider_handler)) as client:
        provider = RazorpayAdapter(
            key_id="rzp_test_composition",
            key_secret="composition-secret",
            client=client,
        )
        with session_factory() as request_session:
            composition = compose_transaction_services(
                request_session=request_session,
                session_factory=session_factory,
                provider_service=provider,
            )
            view = composition.transactions.get_status("txn_1", actor("buyer_1", ActorType.BUYER))
            replay_safe = composition.transactions.execute(
                ExecuteTransactionCommand(
                    transaction_id="txn_1",
                    idempotency_key="composition-execute-1",
                ),
                actor("buyer_1", ActorType.BUYER),
            )

        assert view.id == "txn_1"
        assert replay_safe.state is TransactionState.PAYMENT_PENDING
        assert provider_requests == []
        assert callable(composition.transactions.create)
        assert callable(composition.transactions.execute)
        assert callable(composition.transactions.reconcile)
        assert callable(composition.transactions.get_audit)
        with session_factory() as session:
            idempotency = session.query(models.IdempotencyRecord).one()
            assert idempotency.resource_id == "txn_1"
            assert idempotency.response_code == 200


def _seed(factory) -> None:
    with factory() as session:
        session.add(models.Merchant(id="merch_1", name="Merchant One"))
        session.add(models.Merchant(id="merch_2", name="Merchant Two"))
        session.add(models.Buyer(id="buyer_1", external_identity="buyer-ext-1"))
        session.add(models.Buyer(id="buyer_2", external_identity="buyer-ext-2"))
        session.add(
            models.Product(
                id="prod_1",
                merchant_id="merch_1",
                sku="GAN-65",
                title="65W GaN Charger",
                description="Two USB-C ports and one USB-A port",
                price_minor=169_900,
                currency="INR",
                available_quantity=25,
                status="PUBLISHED",
                version=1,
            )
        )
        session.add(
            models.Product(
                id="prod_2",
                merchant_id="merch_2",
                sku="OTHER",
                title="Other Merchant Product",
                description="Tenant boundary fixture",
                price_minor=99_900,
                currency="INR",
                available_quantity=5,
                status="PUBLISHED",
                version=1,
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
                unit_price_minor=169_900,
                total_minor=169_900,
                currency="INR",
                proposal_hash="sha256:proposal",
                status="PROPOSED",
                expires_at=NOW + timedelta(minutes=15),
                created_at=NOW,
            )
        )
        session.add(
            models.Transaction(
                id="txn_1",
                proposal_id="prop_1",
                merchant_id="merch_1",
                buyer_id="buyer_1",
                amount_minor=169_900,
                currency="INR",
                state=TransactionState.PAYMENT_PENDING.value,
                created_at=NOW,
                updated_at=NOW + timedelta(seconds=1),
            )
        )
        session.add(
            models.PurchaseProposal(
                id="prop_2",
                buyer_id="buyer_2",
                merchant_id="merch_2",
                product_id="prod_2",
                product_version=1,
                quantity=1,
                unit_price_minor=99_900,
                total_minor=99_900,
                currency="INR",
                proposal_hash="sha256:proposal-2",
                status="PROPOSED",
                expires_at=NOW + timedelta(minutes=15),
                created_at=NOW,
            )
        )
        session.add(
            models.Transaction(
                id="txn_2",
                proposal_id="prop_2",
                merchant_id="merch_2",
                buyer_id="buyer_2",
                amount_minor=99_900,
                currency="INR",
                state=TransactionState.READY.value,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.add(
            models.PaymentAttempt(
                id="pay_attempt_1",
                transaction_id="txn_1",
                attempt_number=1,
                provider=ProviderName.RAZORPAY.value,
                provider_request_fingerprint="sha256:provider",
                provider_order_id="order_test_123456",
                provider_order_state="created",
                created_at=NOW + timedelta(milliseconds=500),
                updated_at=NOW + timedelta(milliseconds=500),
            )
        )
        for index in range(52):
            session.add(
                models.TransactionEvent(
                    id=f"tevt_{index:03d}",
                    transaction_id="txn_1",
                    event_type=(
                        "TRANSACTION_CREATED" if index == 0 else "TRANSACTION_STATE_CHANGED"
                    ),
                    actor_type=(ActorType.BUYER.value if index == 0 else ActorType.SYSTEM.value),
                    actor_id="buyer_1" if index == 0 else None,
                    reason_code=("GATES_SATISFIED" if index == 0 else "PROVIDER_ATTEMPT_CREATED"),
                    previous_state=None if index == 0 else TransactionState.READY.value,
                    new_state=(
                        TransactionState.READY.value
                        if index == 0
                        else TransactionState.EXECUTING.value
                    ),
                    correlation_id=f"corr_{index:03d}",
                    provider_reference_redacted=None if index == 0 else "...3456",
                    metadata_json={
                        "proposal_id": "prop_1",
                        "merchant_id": "merch_1",
                        "buyer_id": "buyer_1",
                        "amount_minor": 169_900,
                        "currency": "INR",
                    },
                    created_at=NOW + timedelta(milliseconds=index),
                )
            )
        session.add(
            models.TransactionEvent(
                id="tevt_other_transaction",
                transaction_id="txn_2",
                event_type="TRANSACTION_CREATED",
                actor_type=ActorType.BUYER.value,
                actor_id="buyer_2",
                reason_code="GATES_SATISFIED",
                previous_state=None,
                new_state=TransactionState.READY.value,
                correlation_id="corr_other",
                provider_reference_redacted=None,
                metadata_json={
                    "proposal_id": "prop_2",
                    "merchant_id": "merch_2",
                    "buyer_id": "buyer_2",
                    "amount_minor": 99_900,
                    "currency": "INR",
                },
                created_at=NOW,
            )
        )
        session.commit()
