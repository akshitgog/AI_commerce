"""MCP Buyer Server interoperability test over real HTTP transport.

Proves the full transport chain with real authenticated buyer sessions:

    Official MCP Client (+ session token)
        -> Streamable HTTP
    FastAPI/ASGI server
        ->
    /mcp/buyer
        ->
    MCPServer (tool dispatch, session-authenticated actor)
        ->
    composition seam (test fakes in tests; real services in production)
        ->
    Application Services
        ->
    Real response

This is the HTTP interoperability evidence for the buyer MCP surface: an
external-compatible client transacts through the same bounded core as the
reference buyer chat, with identity resolved from the session, never from
arguments.
"""

import asyncio
import json
import socket
from collections.abc import AsyncIterator

import pytest
import uvicorn
from mcp.types import TextContent

from ai_commerce_gateway.api.app import create_app
from ai_commerce_gateway.api.composition import static_bundle_factory
from tests.conftest import (
    fake_service_bundle,
    make_test_settings,
    mcp_buyer_client,
)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
async def running_server() -> AsyncIterator[tuple[str, str]]:
    port = _find_free_port()
    app = create_app(
        services_factory=static_bundle_factory(fake_service_bundle()),
        settings=make_test_settings(),
    )
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    for _ in range(50):
        await asyncio.sleep(0.1)
        if server.started:
            break
    base_url = f"http://127.0.0.1:{port}"
    try:
        yield base_url, f"{base_url}/mcp/buyer/"
    finally:
        server.should_exit = True
        await task


@pytest.mark.anyio
async def test_interop_full_buyer_journey_over_http(
    running_server: tuple[str, str],
) -> None:
    """Full buyer sequence via MCP over HTTP with a real buyer session."""
    _, mcp_url = running_server

    async with mcp_buyer_client(mcp_url, "buyer_interop_1") as client:
        # ---- initialize + tools/list: exactly 7 buyer tools ----
        tools = await client.list_tools()
        tool_names = sorted([t.name for t in tools.tools])
        assert len(tool_names) == 7
        assert "search_catalog" in tool_names
        assert "create_purchase_proposal" in tool_names
        # no approval / merchant / provider tools
        assert "approve_authorization" not in tool_names
        assert "publish_product" not in tool_names

        # ---- search_catalog ----
        search_result = await client.call_tool(
            "search_catalog",
            {"merchant_id": "mer_1"},
        )
        assert search_result.is_error is not True
        search_text = search_result.content[0]
        assert isinstance(search_text, TextContent)
        search_data = json.loads(search_text.text)
        assert len(search_data["items"]) > 0
        product_id = search_data["items"][0]["id"]

        # ---- get_product ----
        product_result = await client.call_tool(
            "get_product",
            {"merchant_id": search_data["items"][0]["merchant_id"], "product_id": product_id},
        )
        product_data = json.loads(product_result.content[0].text)  # type: ignore[index]
        assert product_data["id"] == product_id

        # ---- create_purchase_proposal: server-derived price, session buyer ----
        proposal_result = await client.call_tool(
            "create_purchase_proposal",
            {"merchant_id": "mer_1", "product_id": product_id, "quantity": 2},
        )
        proposal_data = json.loads(proposal_result.content[0].text)  # type: ignore[index]
        assert proposal_data["product_id"] == product_id
        assert proposal_data["buyer_id"] == "buyer_interop_1"  # from session, not args
        assert proposal_data["total"]["amount_minor"] == 2000  # server-derived
        proposal_id = proposal_data["id"]

        # ---- request_authorization (NOT approve) ----
        auth_result = await client.call_tool(
            "request_authorization", {"proposal_id": proposal_id}
        )
        auth_data = json.loads(auth_result.content[0].text)  # type: ignore[index]
        assert auth_data["status"] == "REQUESTED"
        assert auth_data["buyer_id"] == "buyer_interop_1"

        # ---- execute_transaction ----
        exec_result = await client.call_tool(
            "execute_transaction", {"proposal_id": proposal_id}
        )
        exec_data = json.loads(exec_result.content[0].text)  # type: ignore[index]
        transaction_id = exec_data["id"]

        # ---- get_transaction_status ----
        status_result = await client.call_tool(
            "get_transaction_status", {"transaction_id": transaction_id}
        )
        status_data = json.loads(status_result.content[0].text)  # type: ignore[index]
        assert status_data["id"] == transaction_id

        # ---- get_transaction_audit ----
        audit_result = await client.call_tool(
            "get_transaction_audit", {"transaction_id": transaction_id}
        )
        audit_data = json.loads(audit_result.content[0].text)  # type: ignore[index]
        assert "items" in audit_data


@pytest.mark.anyio
async def test_interop_rejects_unauthenticated_calls(
    running_server: tuple[str, str],
) -> None:
    """A client with no session token cannot invoke any tool."""
    _, mcp_url = running_server
    async with mcp_buyer_client(mcp_url, None) as client:
        for tool, args in [
            ("search_catalog", {"merchant_id": "mer_1"}),
            ("create_purchase_proposal", {"merchant_id": "m", "product_id": "p"}),
            ("get_transaction_status", {"transaction_id": "txn_1"}),
        ]:
            result = await client.call_tool(tool, args)
            assert result.is_error is True, f"{tool} should require authentication"


@pytest.mark.anyio
async def test_interop_buyer_identity_isolated_per_session(
    running_server: tuple[str, str],
) -> None:
    """Two concurrent sessions must not leak identity across the same server."""
    _, mcp_url = running_server

    async with mcp_buyer_client(mcp_url, "buyer_anna") as anna:
        async with mcp_buyer_client(mcp_url, "buyer_omar") as omar:
            anna_prop = await anna.call_tool(
                "create_purchase_proposal",
                {"merchant_id": "mer_1", "product_id": "prod_fake_001", "quantity": 1},
            )
            omar_prop = await omar.call_tool(
                "create_purchase_proposal",
                {"merchant_id": "mer_1", "product_id": "prod_fake_001", "quantity": 1},
            )
            anna_data = json.loads(anna_prop.content[0].text)  # type: ignore[index]
            omar_data = json.loads(omar_prop.content[0].text)  # type: ignore[index]
            assert anna_data["buyer_id"] == "buyer_anna"
            assert omar_data["buyer_id"] == "buyer_omar"
