"""Merchant MCP Server (C7) — disjoint adapter over the merchant catalog service.

Exposes exactly six merchant catalog tools over Streamable HTTP:

    create_product_draft, update_product, get_product, list_products,
    publish_product, unpublish_product

Security model:

* Disjoint registry: this server shares NO tools with the buyer MCP server.
  There are no buyer financial, provider, transaction, webhook, or policy
  admin tools here.
* Identity: the caller's merchant session bearer token is extracted from the
  request and forwarded to the trusted merchant service, which resolves
  membership and enforces roles (reads: any member; mutations: ADMIN/EDITOR)
  server-side. The header value is never trusted as identity and no merchant
  identity is ever taken from tool arguments beyond routing.
* Mutations require a transport-level ``Idempotency-Key`` header; it is
  forwarded into the merchant service's idempotent mutation contract.
* Publication tokens (``confirmation_token``) are accepted by publish and
  unpublish, forwarded to the merchant service (which verifies, binds and
  burns them), and are never echoed in results or logs — stripped at this
  adapter boundary.
"""

import json
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.exceptions import ToolError

from ai_commerce_gateway.contracts.models import Money, ProductView
from ai_commerce_gateway.core.errors import AppError
from ai_commerce_gateway.infrastructure.http.merchant_api_client import MerchantApiClient

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

_AUTH_REQUIRED = (
    "A valid merchant session is required (Authorization: Bearer <merchant session token>)."
)
_IDEMPOTENCY_REQUIRED = "Idempotency-Key header is required for merchant catalog mutations."


def _auth_token(ctx: Context) -> str:
    """Extract the caller's merchant session token from the request.

    The token is forwarded to the trusted merchant service for verification;
    it is never parsed or trusted as identity here.
    """
    headers = ctx.headers
    if headers is None:
        raise ToolError(_AUTH_REQUIRED)
    authorization = headers.get("authorization") or headers.get("Authorization")
    if not authorization:
        raise ToolError(_AUTH_REQUIRED)
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ToolError(_AUTH_REQUIRED)
    return token.strip()


def _idempotency_key(ctx: Context) -> str:
    """Require the transport-level Idempotency-Key header for mutations."""
    headers = ctx.headers or {}
    key = headers.get("idempotency-key") or headers.get("Idempotency-Key")
    if not key or not key.strip():
        raise ToolError(_IDEMPOTENCY_REQUIRED)
    return key.strip()


def _product_text(product: ProductView) -> str:
    """Serialize a ProductView. Never includes any confirmation token."""
    return json.dumps(product.model_dump(), default=str)


def _call[T](fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run a merchant service call, translating errors into tool errors."""
    try:
        return fn(*args, **kwargs)
    except AppError as exc:
        raise ToolError(f"{exc.code}: {exc.message}") from exc


def create_merchant_mcp_server(api_client: MerchantApiClient) -> MCPServer:
    """Create the Merchant MCP server with exactly the 6 catalog tools."""

    mcp = MCPServer("ai-commerce-merchant")

    @mcp.tool()
    def create_product_draft(
        ctx: Context,
        merchant_id: str,
        sku: str,
        title: str,
        description: str,
        price_amount_minor: int,
        currency: str,
        available_quantity: int,
        category: str | None = None,
    ) -> str:
        """Create a product in DRAFT status. Requires ADMIN/EDITOR and a
        transport-level Idempotency-Key header. Never publishes."""
        token = _auth_token(ctx)
        idem = _idempotency_key(ctx)
        product = _call(
            api_client.create_product_draft,
            merchant_id=merchant_id,
            auth_token=token,
            idempotency_key=idem,
            sku=sku,
            title=title,
            description=description,
            price=Money(amount_minor=price_amount_minor, currency=currency),
            available_quantity=available_quantity,
            category=category,
        )
        return _product_text(product)

    @mcp.tool()
    def update_product(
        ctx: Context,
        merchant_id: str,
        product_id: str,
        expected_version: int,
        title: str | None = None,
        description: str | None = None,
        category: str | None = None,
        price_amount_minor: int | None = None,
        currency: str | None = None,
        available_quantity: int | None = None,
    ) -> str:
        """Update product fields. Requires ADMIN/EDITOR and Idempotency-Key.
        expected_version guards against lost updates."""
        token = _auth_token(ctx)
        idem = _idempotency_key(ctx)
        price = None
        if price_amount_minor is not None:
            if currency is None:
                raise ToolError("currency is required when price_amount_minor is given.")
            price = Money(amount_minor=price_amount_minor, currency=currency)
        product = _call(
            api_client.update_product,
            merchant_id=merchant_id,
            product_id=product_id,
            auth_token=token,
            idempotency_key=idem,
            expected_version=expected_version,
            title=title,
            description=description,
            category=category,
            price=price,
            available_quantity=available_quantity,
        )
        return _product_text(product)

    @mcp.tool()
    def get_product(ctx: Context, merchant_id: str, product_id: str) -> str:
        """Retrieve a product. Available to any member of the merchant."""
        token = _auth_token(ctx)
        product = _call(
            api_client.get_product,
            merchant_id=merchant_id,
            product_id=product_id,
            auth_token=token,
        )
        return _product_text(product)

    @mcp.tool()
    def list_products(
        ctx: Context, merchant_id: str, cursor: str | None = None
    ) -> str:
        """List the merchant's products (all statuses). Members only."""
        token = _auth_token(ctx)
        page = _call(
            api_client.list_products,
            merchant_id=merchant_id,
            auth_token=token,
            cursor=cursor,
        )
        return json.dumps(
            {
                "items": [p.model_dump() for p in page.items],
                "next_cursor": page.next_cursor,
            },
            default=str,
        )

    @mcp.tool()
    def publish_product(
        ctx: Context,
        merchant_id: str,
        product_id: str,
        expected_version: int,
        confirmation_token: str,
    ) -> str:
        """Publish a product with a dashboard-issued confirmation token.

        The token is verified, bound and burned by the merchant service; it
        is stripped at this boundary and never returned or logged.
        Requires ADMIN/EDITOR and Idempotency-Key.
        """
        token = _auth_token(ctx)
        idem = _idempotency_key(ctx)
        product = _call(
            api_client.publish_product,
            merchant_id=merchant_id,
            product_id=product_id,
            auth_token=token,
            idempotency_key=idem,
            expected_version=expected_version,
            confirmation_token=confirmation_token,
        )
        return _product_text(product)

    @mcp.tool()
    def unpublish_product(
        ctx: Context,
        merchant_id: str,
        product_id: str,
        expected_version: int,
        confirmation_token: str,
    ) -> str:
        """Unpublish a product with a dashboard-issued confirmation token.
        Same boundary and role rules as publish_product."""
        token = _auth_token(ctx)
        idem = _idempotency_key(ctx)
        product = _call(
            api_client.unpublish_product,
            merchant_id=merchant_id,
            product_id=product_id,
            auth_token=token,
            idempotency_key=idem,
            expected_version=expected_version,
            confirmation_token=confirmation_token,
        )
        return _product_text(product)

    return mcp
