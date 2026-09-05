"""Buyer MCP Server — thin adapter over the composition seam via the official MCP SDK.

Exposes the 7 canonical buyer tools over Streamable HTTP. Each tool maps
one-to-one to BuyerAdapter methods over the same real application services
used by buyer chat and the buyer UI API. No business logic lives here.

Identity (P0-4): the acting buyer comes ONLY from the authenticated session.
The SDK injects the HTTP request into the tool ``Context``; the
``Authorization`` header is extracted and verified server-side against the
HMAC buyer session service. The header value is never trusted as identity —
it is treated as an untrusted credential and verified before use. Without a
valid session the tool call is rejected. There is no demo buyer fallback.
"""

import hashlib
import json
import logging
from uuid import uuid4

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.exceptions import ToolError

from ai_commerce_gateway.api.composition import BuyerServiceBundle, BuyerServicesFactory
from ai_commerce_gateway.api.session_auth import BuyerSessionService
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

logger = logging.getLogger(__name__)

_AUTH_REQUIRED = "A valid buyer session is required (Authorization: Bearer <session token>)."


def _actor_from_context(ctx: Context, session_service: BuyerSessionService | None) -> ActorContext:
    """Resolve the authenticated buyer actor from the MCP request context.

    ``ctx.headers`` is the raw client-supplied header map; the session token
    it carries is verified server-side and never treated as identity by
    itself. A non-HTTP transport (no headers) cannot carry a session and is
    rejected.
    """
    if session_service is None:
        raise ToolError(_AUTH_REQUIRED)
    headers = ctx.headers
    if headers is None:
        raise ToolError(_AUTH_REQUIRED)
    authorization = headers.get("authorization") or headers.get("Authorization")
    if not authorization:
        raise ToolError(_AUTH_REQUIRED)
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ToolError(_AUTH_REQUIRED)
    correlation_id = (
        headers.get("x-correlation-id")
        or headers.get("X-Correlation-ID")
        or f"corr_{uuid4().hex[:12]}"
    )
    actor = session_service.actor_context(token.strip(), correlation_id=correlation_id)
    if actor is None:
        raise ToolError(_AUTH_REQUIRED)
    return actor


def _invocation_from_context(ctx: Context, idempotency_key: str | None = None) -> InvocationContext:
    headers = ctx.headers or {}
    correlation_id = (
        headers.get("x-correlation-id")
        or headers.get("X-Correlation-ID")
        or f"corr_{uuid4().hex[:12]}"
    )
    return InvocationContext(
        correlation_id=correlation_id,
        idempotency_key=idempotency_key or f"idem_{uuid4().hex}",
        request_id=f"req_{uuid4().hex[:12]}",
    )


def _derive_idempotency_key(actor_id: str, tool_name: str, **kwargs: object) -> str:
    """Derive a deterministic idempotency key from the actor and request shape."""
    payload = json.dumps(
        {"actor_id": actor_id, "tool_name": tool_name, "kwargs": kwargs},
        sort_keys=True,
    )
    return "idem_" + hashlib.sha256(payload.encode()).hexdigest()[:16]


def _result_to_text(data: object) -> str:
    """Serialize a result to JSON text for MCP responses."""
    if hasattr(data, "model_dump"):
        return json.dumps(data.model_dump(), default=str)
    return json.dumps(data, default=str)


def create_buyer_mcp_server(
    services_factory: BuyerServicesFactory,
    session_service: BuyerSessionService | None = None,
) -> MCPServer:
    """Create the Buyer MCP server with 7 tools over the composition seam.

    All tools resolve the acting buyer from the authenticated session, never
    from arguments. There are no merchant, provider, approval or admin tools
    on this server.
    """

    mcp = MCPServer("ai-commerce-buyer")

    def _adapter_from(bundle: BuyerServiceBundle) -> BuyerAdapter:
        return BuyerAdapter(
            catalog=bundle.catalog,
            proposal=bundle.proposal,
            auth=bundle.auth,
            transaction=bundle.transaction,
        )

    @mcp.tool()
    def search_catalog(
        ctx: Context,
        merchant_id: str,
        query: str | None = None,
        category: str | None = None,
        min_price_minor: int | None = None,
        max_price_minor: int | None = None,
        currency: str | None = None,
    ) -> str:
        """Search for published products available from the merchant."""
        actor = _actor_from_context(ctx, session_service)
        invocation = _invocation_from_context(ctx)
        req = SearchCatalogRequest(
            merchant_id=merchant_id,
            query=query,
            category=category,
            min_price_minor=min_price_minor,
            max_price_minor=max_price_minor,
            currency=currency,
        )
        with services_factory() as services:
            adapter = _adapter_from(services)
            result = adapter.search_catalog(actor, invocation, req)
        items = [p.model_dump() for p in result.items]
        return json.dumps(
            {"items": items, "next_cursor": result.next_cursor},
            default=str,
        )

    @mcp.tool()
    def get_product(ctx: Context, merchant_id: str, product_id: str) -> str:
        """Retrieve full details of a specific published product."""
        actor = _actor_from_context(ctx, session_service)
        invocation = _invocation_from_context(ctx)
        req = GetProductRequest(merchant_id=merchant_id, product_id=product_id)
        with services_factory() as services:
            adapter = _adapter_from(services)
            result = adapter.get_product(actor, invocation, req)
        return _result_to_text(result)

    @mcp.tool()
    def create_purchase_proposal(
        ctx: Context,
        merchant_id: str,
        product_id: str,
        quantity: int = 1,
    ) -> str:
        """Create an immutable purchase proposal. AI cannot derive price."""
        actor = _actor_from_context(ctx, session_service)
        idem_key = _derive_idempotency_key(
            actor.actor_id,
            "create_purchase_proposal",
            merchant_id=merchant_id,
            product_id=product_id,
            quantity=quantity,
        )
        invocation = _invocation_from_context(ctx, idempotency_key=idem_key)
        req = CreatePurchaseProposalRequest(
            merchant_id=merchant_id,
            product_id=product_id,
            quantity=quantity,
        )
        with services_factory() as services:
            adapter = _adapter_from(services)
            result = adapter.create_purchase_proposal(actor, invocation, req)
        return _result_to_text(result)

    @mcp.tool()
    def request_authorization(ctx: Context, proposal_id: str) -> str:
        """Request human buyer authorization for a proposal. Cannot approve."""
        actor = _actor_from_context(ctx, session_service)
        idem_key = _derive_idempotency_key(
            actor.actor_id,
            "request_authorization",
            proposal_id=proposal_id,
        )
        invocation = _invocation_from_context(ctx, idempotency_key=idem_key)
        req = RequestAuthorizationRequest(proposal_id=proposal_id)
        with services_factory() as services:
            adapter = _adapter_from(services)
            result = adapter.request_authorization(actor, invocation, req)
        return _result_to_text(result)

    @mcp.tool()
    def execute_transaction(ctx: Context, proposal_id: str) -> str:
        """Execute a transaction for an authorized proposal."""
        actor = _actor_from_context(ctx, session_service)
        idem_key = _derive_idempotency_key(
            actor.actor_id,
            "execute_transaction",
            proposal_id=proposal_id,
        )
        invocation = _invocation_from_context(ctx, idempotency_key=idem_key)
        req = ExecuteTransactionRequest(proposal_id=proposal_id)
        with services_factory() as services:
            adapter = _adapter_from(services)
            result = adapter.execute_transaction(actor, invocation, req)
        return _result_to_text(result)

    @mcp.tool()
    def get_transaction_status(ctx: Context, transaction_id: str) -> str:
        """Check the status of a transaction."""
        actor = _actor_from_context(ctx, session_service)
        invocation = _invocation_from_context(ctx)
        req = GetTransactionStatusRequest(transaction_id=transaction_id)
        with services_factory() as services:
            adapter = _adapter_from(services)
            result = adapter.get_transaction_status(actor, invocation, req)
        return _result_to_text(result)

    @mcp.tool()
    def get_transaction_audit(
        ctx: Context,
        transaction_id: str,
        cursor: str | None = None,
    ) -> str:
        """Retrieve audit log events for a transaction."""
        actor = _actor_from_context(ctx, session_service)
        invocation = _invocation_from_context(ctx)
        req = GetTransactionAuditRequest(
            transaction_id=transaction_id,
            cursor=cursor,
        )
        with services_factory() as services:
            adapter = _adapter_from(services)
            result = adapter.get_transaction_audit(actor, invocation, req)
        items = [e.model_dump() for e in result.items]
        return json.dumps(
            {"items": items, "next_cursor": result.next_cursor},
            default=str,
        )

    return mcp
