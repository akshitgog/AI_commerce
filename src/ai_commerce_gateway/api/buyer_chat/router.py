"""Buyer Chat HTTP router.

Maps the 7 canonical buyer tool operations to FastAPI endpoints.
Each route:
  1. Extracts ActorContext from server-validated session middleware.
  2. Extracts InvocationContext (correlation_id, idempotency_key) from HTTP headers.
  3. Constructs the typed request schema from the body.
  4. Delegates to BuyerAdapter — which in turn calls canonical application
     services obtained per request from the composition seam on
     ``app.state.buyer_services_factory``.
  5. Returns the canonical response, always including correlation_id.

No financial logic lives here. No provider calls. No authorization grants.
"""

from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from ai_commerce_gateway.api.buyer_chat.dependencies import (
    get_buyer_actor,
    get_invocation_context,
)
from ai_commerce_gateway.api.composition import BuyerServiceBundle
from ai_commerce_gateway.application.buyer_adapter.adapter import BuyerAdapter
from ai_commerce_gateway.application.buyer_adapter.llm_client import create_llm_client
from ai_commerce_gateway.application.buyer_adapter.orchestrator import ToolOrchestrator
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
from ai_commerce_gateway.contracts.models import ActorContext

router = APIRouter(prefix="/buyer", tags=["buyer-chat"])


# ---------------------------------------------------------------------------
# Dependencies: composition seam (real services only; fakes in tests)
# ---------------------------------------------------------------------------


def get_buyer_services(request: Request) -> Iterator[BuyerServiceBundle]:
    """Open the request-scoped application service bundle.

    The context manager owns the unit of work: in-process composition
    commits/rolls back the request session here, remote composition is a
    no-op boundary. There is deliberately no stub fallback.
    """
    factory = getattr(request.app.state, "buyer_services_factory", None)
    if factory is None:
        raise RuntimeError(
            "Buyer services factory is not configured on app.state. "
            "create_app() must receive a BuyerServicesFactory or valid "
            "buyer_services configuration."
        )
    with factory() as bundle:
        yield bundle


def get_buyer_adapter(
    services: Annotated[BuyerServiceBundle, Depends(get_buyer_services)],
) -> BuyerAdapter:
    return BuyerAdapter(
        catalog=services.catalog,
        proposal=services.proposal,
        auth=services.auth,
        transaction=services.transaction,
    )


def get_tool_orchestrator(
    adapter: Annotated[BuyerAdapter, Depends(get_buyer_adapter)],
) -> ToolOrchestrator:
    """Build the bounded orchestrator with the configured LLM client.

    The client comes from YAML configuration (``llm.*``); the step bound comes
    from ``llm.max_tool_steps``. The deterministic fallback is used only when
    no API key is configured and is logged loudly.
    """
    from ai_commerce_gateway.core.config import get_settings

    settings = get_settings()
    return ToolOrchestrator(
        llm_client=create_llm_client(settings),
        adapter=adapter,
        max_tool_steps=settings.llm_max_tool_steps,
    )


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class SearchCatalogBody(BaseModel):
    merchant_id: str
    query: str | None = None
    category: str | None = None
    min_price_minor: int | None = Field(default=None, ge=0)
    max_price_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")


class CreateProposalBody(BaseModel):
    merchant_id: str
    product_id: str
    quantity: int = Field(default=1, ge=1)
    # Intentionally NO price, total, or trusted financial fields.


class RequestAuthorizationBody(BaseModel):
    proposal_id: str


class ExecuteTransactionBody(BaseModel):
    proposal_id: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequestBody(BaseModel):
    messages: list[ChatMessage]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/catalog/search")
def search_catalog(
    body: SearchCatalogBody,
    actor: Annotated[ActorContext, Depends(get_buyer_actor)],
    invocation: Annotated[InvocationContext, Depends(get_invocation_context)],
    adapter: Annotated[BuyerAdapter, Depends(get_buyer_adapter)],
) -> dict[str, Any]:
    req = SearchCatalogRequest(
        merchant_id=body.merchant_id,
        query=body.query,
        category=body.category,
        min_price_minor=body.min_price_minor,
        max_price_minor=body.max_price_minor,
        currency=body.currency,
    )
    result = adapter.search_catalog(actor, invocation, req)
    return {
        "items": [p.model_dump() for p in result.items],
        "next_cursor": result.next_cursor,
        "correlation_id": invocation.correlation_id,
    }


@router.get("/catalog/products/{product_id}")
def get_product(
    product_id: str,
    actor: Annotated[ActorContext, Depends(get_buyer_actor)],
    invocation: Annotated[InvocationContext, Depends(get_invocation_context)],
    adapter: Annotated[BuyerAdapter, Depends(get_buyer_adapter)],
) -> dict[str, Any]:
    req = GetProductRequest(product_id=product_id)
    product = adapter.get_product(actor, invocation, req)
    return {**product.model_dump(), "correlation_id": invocation.correlation_id}


@router.post("/purchase-proposals")
def create_purchase_proposal(
    body: CreateProposalBody,
    actor: Annotated[ActorContext, Depends(get_buyer_actor)],
    invocation: Annotated[InvocationContext, Depends(get_invocation_context)],
    adapter: Annotated[BuyerAdapter, Depends(get_buyer_adapter)],
) -> dict[str, Any]:
    req = CreatePurchaseProposalRequest(
        merchant_id=body.merchant_id,
        product_id=body.product_id,
        quantity=body.quantity,
    )
    proposal = adapter.create_purchase_proposal(actor, invocation, req)
    return {**proposal.model_dump(), "correlation_id": invocation.correlation_id}


@router.post("/purchase-proposals/{proposal_id}/authorization-requests")
def request_authorization(
    proposal_id: str,
    actor: Annotated[ActorContext, Depends(get_buyer_actor)],
    invocation: Annotated[InvocationContext, Depends(get_invocation_context)],
    adapter: Annotated[BuyerAdapter, Depends(get_buyer_adapter)],
) -> dict[str, Any]:
    req = RequestAuthorizationRequest(proposal_id=proposal_id)
    auth = adapter.request_authorization(actor, invocation, req)
    return {**auth.model_dump(), "correlation_id": invocation.correlation_id}


@router.post("/transactions")
def execute_transaction(
    body: ExecuteTransactionBody,
    actor: Annotated[ActorContext, Depends(get_buyer_actor)],
    invocation: Annotated[InvocationContext, Depends(get_invocation_context)],
    adapter: Annotated[BuyerAdapter, Depends(get_buyer_adapter)],
) -> dict[str, Any]:
    req = ExecuteTransactionRequest(proposal_id=body.proposal_id)
    txn = adapter.execute_transaction(actor, invocation, req)
    return {**txn.model_dump(), "correlation_id": invocation.correlation_id}


@router.get("/transactions/{transaction_id}")
def get_transaction_status(
    transaction_id: str,
    actor: Annotated[ActorContext, Depends(get_buyer_actor)],
    invocation: Annotated[InvocationContext, Depends(get_invocation_context)],
    adapter: Annotated[BuyerAdapter, Depends(get_buyer_adapter)],
) -> dict[str, Any]:
    req = GetTransactionStatusRequest(transaction_id=transaction_id)
    txn = adapter.get_transaction_status(actor, invocation, req)
    return {**txn.model_dump(), "correlation_id": invocation.correlation_id}


@router.get("/transactions/{transaction_id}/events")
def get_transaction_audit(
    transaction_id: str,
    cursor: str | None = Query(default=None),
    actor: Annotated[ActorContext, Depends(get_buyer_actor)] = ...,  # type: ignore[assignment]
    invocation: Annotated[InvocationContext, Depends(get_invocation_context)] = ...,  # type: ignore[assignment]
    adapter: Annotated[BuyerAdapter, Depends(get_buyer_adapter)] = ...,  # type: ignore[assignment]
) -> dict[str, Any]:
    req = GetTransactionAuditRequest(transaction_id=transaction_id, cursor=cursor)
    page = adapter.get_transaction_audit(actor, invocation, req)
    return {
        "items": [e.model_dump() for e in page.items],
        "next_cursor": page.next_cursor,
        "correlation_id": invocation.correlation_id,
    }


@router.post("/chat")
def chat(
    body: ChatRequestBody,
    actor: Annotated[ActorContext, Depends(get_buyer_actor)],
    invocation: Annotated[InvocationContext, Depends(get_invocation_context)],
    orchestrator: Annotated[ToolOrchestrator, Depends(get_tool_orchestrator)],
) -> dict[str, Any]:
    messages = [m.model_dump() for m in body.messages]
    result = orchestrator.chat(actor, invocation, messages)
    return {
        **result,
        "correlation_id": invocation.correlation_id,
    }
