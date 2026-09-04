"""MCP Buyer Server interoperability test over real HTTP transport.

This test mounts the MCP ASGI app in a real ASGI test server and connects
an official MCP Client via Streamable HTTP URL. This proves the full
transport chain:

    Official MCP Client
        ↓ Streamable HTTP
    FastAPI/ASGI test server
        ↓
    /mcp/buyer
        ↓
    MCPServer (tool dispatch)
        ↓
    BuyerAdapter
        ↓
    Application Services (stubs)
        ↓
    Real response
"""

import asyncio
import json
import socket

import pytest
import uvicorn
from mcp.client import Client
from mcp.types import TextContent


def _find_free_port() -> int:
    """Find a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _build_fresh_app():  # type: ignore[no-untyped-def]
    """Build a fresh FastAPI app instance to avoid session_manager reuse."""
    import contextlib
    from collections.abc import AsyncIterator

    from fastapi import FastAPI

    from ai_commerce_gateway.api.buyer_chat.stubs import (
        get_auth_service,
        get_catalog_service,
        get_proposal_service,
        get_transaction_service,
    )
    from ai_commerce_gateway.api.mcp.buyer_server import (
        create_buyer_mcp_server,
    )
    from ai_commerce_gateway.application.buyer_adapter.adapter import (
        BuyerAdapter,
    )

    adapter = BuyerAdapter(
        catalog=get_catalog_service(),
        proposal=get_proposal_service(),
        auth=get_auth_service(),
        transaction=get_transaction_service(),
    )
    buyer_mcp = create_buyer_mcp_server(adapter)
    mcp_app = buyer_mcp.streamable_http_app(
        streamable_http_path="/",
    )

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with buyer_mcp.session_manager.run():
            yield

    app = FastAPI(lifespan=lifespan)
    app.mount("/mcp/buyer", mcp_app)
    return app


@pytest.mark.anyio
async def test_interop_full_buyer_journey_over_http() -> None:
    """Prove both search_catalog and create_purchase_proposal work
    through the real HTTP transport in a single server session.

    Completion gate evidence:
    1. Client → HTTP → /mcp/buyer → initialize → tools/list →
       7 tools → search_catalog → BuyerAdapter → CatalogService →
       real response
    2. Client → create_purchase_proposal → BuyerAdapter →
       ProposalService → trusted proposal
    """
    port = _find_free_port()
    app = _build_fresh_app()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="error",
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    # Wait for the server to start
    for _ in range(50):
        await asyncio.sleep(0.1)
        if server.started:
            break

    try:
        mcp_url = f"http://127.0.0.1:{port}/mcp/buyer/"
        async with Client(mcp_url) as client:
            # ---- Step 1: initialize + tools/list ----
            tools = await client.list_tools()
            tool_names = sorted([t.name for t in tools.tools])
            assert len(tool_names) == 7
            assert "search_catalog" in tool_names
            assert "create_purchase_proposal" in tool_names

            # ---- Step 2: search_catalog ----
            search_result = await client.call_tool(
                "search_catalog",
                {"merchant_id": "mer_demo_001"},
            )
            assert len(search_result.content) > 0
            text_content = search_result.content[0]
            assert isinstance(text_content, TextContent)
            search_data = json.loads(text_content.text)
            assert "items" in search_data
            assert len(search_data["items"]) > 0
            assert search_data["items"][0]["title"] == "Demo Widget"

            # ---- Step 3: create_purchase_proposal ----
            proposal_result = await client.call_tool(
                "create_purchase_proposal",
                {
                    "merchant_id": "mer_demo_001",
                    "product_id": "prod_demo_001",
                    "quantity": 1,
                },
            )
            assert len(proposal_result.content) > 0
            text_content = proposal_result.content[0]
            assert isinstance(text_content, TextContent)
            proposal_data = json.loads(text_content.text)
            assert "id" in proposal_data
            assert proposal_data["product_id"] == "prod_demo_001"
            # Server-derived price, not client-supplied
            assert proposal_data["unit_price"]["amount_minor"] == 49900
            assert proposal_data["total"]["amount_minor"] == 49900
    finally:
        server.should_exit = True
        await task
