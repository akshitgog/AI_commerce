"""Buyer MCP Server — thin adapter over BuyerAdapter via the official MCP SDK.

Exposes the 7 canonical buyer tools over Streamable HTTP. Each tool maps
one-to-one to BuyerAdapter methods. No business logic lives here.

Identity note: X-Buyer-ID is DEMO IDENTITY PLUMBING only, not trusted
production authentication. A real deployment would use a server-side
session/token mechanism.
"""

import hashlib
import json
import logging
from uuid import uuid4

from mcp.server.mcpserver import MCPServer

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
from ai_commerce_gateway.domain.enums import ActorType

logger = logging.getLogger(__name__)

# Default demo buyer ID when none is provided via transport context
_DEFAULT_DEMO_BUYER = "buyer_demo_001"


def _make_actor(buyer_id: str | None = None) -> ActorContext:
    """Build a demo ActorContext. X-Buyer-ID is demo plumbing only."""
    bid = buyer_id or _DEFAULT_DEMO_BUYER
    return ActorContext(
        actor_id=bid,
        actor_type=ActorType.BUYER,
        correlation_id=f"corr_{uuid4().hex[:12]}",
    )


def _make_invocation(
    idempotency_key: str | None = None,
) -> InvocationContext:
    """Build an InvocationContext for the MCP call."""
    return InvocationContext(
        correlation_id=f"corr_{uuid4().hex[:12]}",
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


def create_buyer_mcp_server(adapter: BuyerAdapter) -> MCPServer:
    """Create and configure the Buyer MCP server with 7 tools."""
    mcp = MCPServer("ai-commerce-buyer")

    @mcp.tool()
    def search_catalog(
        merchant_id: str,
        query: str | None = None,
        category: str | None = None,
        min_price_minor: int | None = None,
        max_price_minor: int | None = None,
        currency: str | None = None,
    ) -> str:
        """Search for published products available from the merchant."""
        actor = _make_actor()
        invocation = _make_invocation()
        req = SearchCatalogRequest(
            merchant_id=merchant_id,
            query=query,
            category=category,
            min_price_minor=min_price_minor,
            max_price_minor=max_price_minor,
            currency=currency,
        )
        result = adapter.search_catalog(actor, invocation, req)
        items = [p.model_dump() for p in result.items]
        return json.dumps(
            {"items": items, "next_cursor": result.next_cursor},
            default=str,
        )

    @mcp.tool()
    def get_product(product_id: str) -> str:
        """Retrieve full details of a specific published product."""
        actor = _make_actor()
        invocation = _make_invocation()
        req = GetProductRequest(product_id=product_id)
        result = adapter.get_product(actor, invocation, req)
        return _result_to_text(result)

    @mcp.tool()
    def create_purchase_proposal(
        merchant_id: str,
        product_id: str,
        quantity: int = 1,
    ) -> str:
        """Create an immutable purchase proposal. AI cannot derive price."""
        actor = _make_actor()
        idem_key = _derive_idempotency_key(
            actor.actor_id,
            "create_purchase_proposal",
            merchant_id=merchant_id,
            product_id=product_id,
            quantity=quantity,
        )
        invocation = _make_invocation(idempotency_key=idem_key)
        req = CreatePurchaseProposalRequest(
            merchant_id=merchant_id,
            product_id=product_id,
            quantity=quantity,
        )
        result = adapter.create_purchase_proposal(actor, invocation, req)
        return _result_to_text(result)

    @mcp.tool()
    def request_authorization(proposal_id: str) -> str:
        """Request human buyer authorization for a proposal. Cannot approve."""
        actor = _make_actor()
        idem_key = _derive_idempotency_key(
            actor.actor_id,
            "request_authorization",
            proposal_id=proposal_id,
        )
        invocation = _make_invocation(idempotency_key=idem_key)
        req = RequestAuthorizationRequest(proposal_id=proposal_id)
        result = adapter.request_authorization(actor, invocation, req)
        return _result_to_text(result)

    @mcp.tool()
    def execute_transaction(proposal_id: str) -> str:
        """Execute a transaction for an authorized proposal."""
        actor = _make_actor()
        idem_key = _derive_idempotency_key(
            actor.actor_id,
            "execute_transaction",
            proposal_id=proposal_id,
        )
        invocation = _make_invocation(idempotency_key=idem_key)
        req = ExecuteTransactionRequest(proposal_id=proposal_id)
        result = adapter.execute_transaction(actor, invocation, req)
        return _result_to_text(result)

    @mcp.tool()
    def get_transaction_status(transaction_id: str) -> str:
        """Check the status of a transaction."""
        actor = _make_actor()
        invocation = _make_invocation()
        req = GetTransactionStatusRequest(transaction_id=transaction_id)
        result = adapter.get_transaction_status(actor, invocation, req)
        return _result_to_text(result)

    @mcp.tool()
    def get_transaction_audit(
        transaction_id: str,
        cursor: str | None = None,
    ) -> str:
        """Retrieve audit log events for a transaction."""
        actor = _make_actor()
        invocation = _make_invocation()
        req = GetTransactionAuditRequest(
            transaction_id=transaction_id,
            cursor=cursor,
        )
        result = adapter.get_transaction_audit(actor, invocation, req)
        items = [e.model_dump() for e in result.items]
        return json.dumps(
            {"items": items, "next_cursor": result.next_cursor},
            default=str,
        )

    return mcp
