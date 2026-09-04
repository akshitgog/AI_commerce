"""Buyer Chat HTTP router.

Maps the 7 canonical buyer tool operations to FastAPI endpoints.
Each route:
  1. Extracts ActorContext from server-validated session (X-Buyer-ID header in demo).
  2. Extracts InvocationContext (correlation_id, idempotency_key) from HTTP headers.
  3. Constructs the typed request schema from the body.
  4. Delegates to BuyerAdapter — which in turn calls canonical application services.
  5. Returns the canonical response, always including correlation_id.

No financial logic lives here. No provider calls. No authorization grants.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ai_commerce_gateway.api.buyer_chat.dependencies import (
    get_buyer_actor,
    get_invocation_context,
)
from ai_commerce_gateway.api.buyer_chat.stubs import (
    get_auth_service,
    get_catalog_service,
    get_proposal_service,
    get_transaction_service,
)
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
from ai_commerce_gateway.contracts.models import ActorContext
from ai_commerce_gateway.contracts.services import (
    AuthorizationService,
    CatalogService,
    ProposalService,
    TransactionService,
)

router = APIRouter(prefix="/buyer", tags=["buyer-chat"])


# ---------------------------------------------------------------------------
# Dependency: BuyerAdapter
# ---------------------------------------------------------------------------


def get_buyer_adapter(
    catalog: Annotated[CatalogService, Depends(get_catalog_service)],
    proposal: Annotated[ProposalService, Depends(get_proposal_service)],
    auth: Annotated[AuthorizationService, Depends(get_auth_service)],
    transaction: Annotated[TransactionService, Depends(get_transaction_service)],
) -> BuyerAdapter:
    return BuyerAdapter(catalog=catalog, proposal=proposal, auth=auth, transaction=transaction)


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
