import pytest

from ai_commerce_gateway.application.buyer_adapter.adapter import BuyerAdapter
from ai_commerce_gateway.application.buyer_adapter.schemas import (
    CreatePurchaseProposalRequest,
    ExecuteTransactionRequest,
    GetProductRequest,
    GetTransactionAuditRequest,
    GetTransactionStatusRequest,
    InvocationContext,
    RequestAuthorizationRequest,
    SearchCatalogRequest,
)
from ai_commerce_gateway.contracts.models import ActorContext, Money
from ai_commerce_gateway.domain.enums import ActorType, TransactionState

from .fakes import (
    FakeAuthorizationService,
    FakeCatalogService,
    FakeProposalService,
    FakeTransactionService,
)


@pytest.fixture
def adapter() -> BuyerAdapter:
    return BuyerAdapter(
        catalog=FakeCatalogService(),
        proposal=FakeProposalService(),
        auth=FakeAuthorizationService(),
        transaction=FakeTransactionService(),
    )


@pytest.fixture
def actor() -> ActorContext:
    return ActorContext(
        actor_id="buyer_123",
        actor_type=ActorType.BUYER,
        correlation_id="actor_corr_123",
    )


@pytest.fixture
def invocation() -> InvocationContext:
    return InvocationContext(
        correlation_id="corr_123",
        idempotency_key="idem_123",
        request_id="req_123",
    )


def test_search_catalog(
    adapter: BuyerAdapter, actor: ActorContext, invocation: InvocationContext
) -> None:
    request = SearchCatalogRequest(merchant_id="mer_123", query="test")
    result = adapter.search_catalog(actor, invocation, request)
    assert result is not None
    assert isinstance(result.items, tuple)


def test_get_product(
    adapter: BuyerAdapter, actor: ActorContext, invocation: InvocationContext
) -> None:
    request = GetProductRequest(product_id="prod_123")
    result = adapter.get_product(actor, invocation, request)
    assert result.id == "prod_123"
    assert result.price == Money(amount_minor=1000, currency="INR")


def test_create_purchase_proposal(
    adapter: BuyerAdapter, actor: ActorContext, invocation: InvocationContext
) -> None:
    # Client-supplied totals are not accepted by the request schema
    request = CreatePurchaseProposalRequest(
        merchant_id="mer_123", product_id="prod_123", quantity=2
    )
    result = adapter.create_purchase_proposal(actor, invocation, request)

    assert result.product_id == "prod_123"
    assert result.quantity == 2


def test_request_authorization(
    adapter: BuyerAdapter, actor: ActorContext, invocation: InvocationContext
) -> None:
    request = RequestAuthorizationRequest(proposal_id="prop_123")
    result = adapter.request_authorization(actor, invocation, request)

    assert result.proposal_id == "prop_123"


def test_execute_transaction(
    adapter: BuyerAdapter, actor: ActorContext, invocation: InvocationContext
) -> None:
    request = ExecuteTransactionRequest(proposal_id="prop_123")
    result = adapter.execute_transaction(actor, invocation, request)

    assert result.state == TransactionState.EXECUTING


def test_get_transaction_status(
    adapter: BuyerAdapter, actor: ActorContext, invocation: InvocationContext
) -> None:
    request = GetTransactionStatusRequest(transaction_id="txn_123")
    result = adapter.get_transaction_status(actor, invocation, request)

    assert result.id == "txn_123"


def test_get_transaction_audit(
    adapter: BuyerAdapter, actor: ActorContext, invocation: InvocationContext
) -> None:
    request = GetTransactionAuditRequest(transaction_id="txn_123")
    result = adapter.get_transaction_audit(actor, invocation, request)

    assert len(result.items) == 1
    assert result.items[0].provider_reference_redacted == "rzp_order_***123"


def test_map_app_error() -> None:
    from ai_commerce_gateway.application.buyer_adapter.errors import (
        map_app_error,
        map_unknown_error,
    )
    from ai_commerce_gateway.core.errors import AppError, ErrorCode

    exc = AppError(code=ErrorCode.NOT_FOUND, message="Not found", details={"id": "123"})
    res = map_app_error(exc, "corr_123")
    assert res.error.code == ErrorCode.NOT_FOUND
    assert res.correlation_id == "corr_123"

    exc_unk = Exception("Unknown")
    res_unk = map_unknown_error(exc_unk, "corr_123")
    assert res_unk.error.code == ErrorCode.INTERNAL_ERROR
    assert res_unk.correlation_id == "corr_123"


def test_tools_schemas() -> None:
    from ai_commerce_gateway.application.buyer_adapter.tools import ALL_TOOLS

    assert len(ALL_TOOLS) == 7
    names = [t["name"] for t in ALL_TOOLS]
    assert "search_catalog" in names
    assert "create_purchase_proposal" in names


def test_missing_idempotency_key(adapter: BuyerAdapter, actor: ActorContext) -> None:
    invocation = InvocationContext(
        correlation_id="corr_123", idempotency_key=None, request_id="req_123"
    )

    with pytest.raises(ValueError, match="idempotency_key is required"):
        adapter.create_purchase_proposal(
            actor,
            invocation,
            CreatePurchaseProposalRequest(merchant_id="1", product_id="2", quantity=1),
        )

    with pytest.raises(ValueError, match="idempotency_key is required"):
        adapter.request_authorization(
            actor, invocation, RequestAuthorizationRequest(proposal_id="1")
        )

    with pytest.raises(ValueError, match="idempotency_key is required"):
        adapter.execute_transaction(actor, invocation, ExecuteTransactionRequest(proposal_id="1"))
