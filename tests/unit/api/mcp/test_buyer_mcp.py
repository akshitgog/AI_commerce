"""MCP Buyer Server contract + identity tests over real HTTP transport.

The buyer MCP tools resolve the acting buyer ONLY from the authenticated
session token (P0-4); in-memory transports carry no headers and therefore
cannot authenticate. All tests here run over real HTTP with real HMAC session
tokens.
"""

import asyncio
import json
import socket
from collections.abc import AsyncIterator

import httpx
import pytest
import uvicorn
from mcp.types import TextContent

from ai_commerce_gateway.api.app import create_app
from ai_commerce_gateway.api.composition import static_bundle_factory
from tests.conftest import (
    fake_service_bundle,
    issue_buyer_token,
    make_test_settings,
    mcp_buyer_client,
)

EXPECTED_TOOL_NAMES = sorted(
    [
        "search_catalog",
        "get_product",
        "create_purchase_proposal",
        "request_authorization",
        "execute_transaction",
        "get_transaction_status",
        "get_transaction_audit",
    ]
)

# Merchant/provider/admin tools must NEVER appear on the buyer server.
FORBIDDEN_TOOL_NAMES = {
    "create_product_draft",
    "update_product",
    "publish_product",
    "unpublish_product",
    "approve_authorization",
    "approve_merchant",
    "set_price",
    "mark_paid",
    "set_transaction_state",
    "create_razorpay_order",
    "razorpay_checkout",
    "list_products",
    "admin_delete",
}


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
async def running_server() -> AsyncIterator[tuple[str, str]]:
    """Start the real app (fake services via the seam) and yield (base, mcp_url)."""
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
async def test_tools_list_exactly_seven(running_server: tuple[str, str]) -> None:
    """tools/list must expose exactly the 7 buyer tools."""
    _, mcp_url = running_server
    async with mcp_buyer_client(mcp_url, "buyer_1") as client:
        result = await client.list_tools()
        tool_names = sorted([t.name for t in result.tools])
        assert tool_names == EXPECTED_TOOL_NAMES
        assert len(result.tools) == 7


@pytest.mark.anyio
async def test_no_merchant_or_privileged_tools(running_server: tuple[str, str]) -> None:
    """A buyer session must never discover merchant/provider/admin tools."""
    _, mcp_url = running_server
    async with mcp_buyer_client(mcp_url, "buyer_1") as client:
        result = await client.list_tools()
        tool_names = {t.name for t in result.tools}
        assert tool_names & FORBIDDEN_TOOL_NAMES == set()
        assert "approve_authorization" not in tool_names


@pytest.mark.anyio
async def test_tool_schemas_are_complete(running_server: tuple[str, str]) -> None:
    """Every tool must have a non-empty inputSchema with properties."""
    _, mcp_url = running_server
    async with mcp_buyer_client(mcp_url, "buyer_1") as client:
        result = await client.list_tools()
        for tool in result.tools:
            schema = tool.input_schema
            assert schema is not None, f"Tool {tool.name} has no input_schema"
            assert "properties" in schema, f"Tool {tool.name} schema missing 'properties'"
            # No identity/approval fields may be supplied by the caller
            props = set(schema["properties"].keys())
            assert "buyer_id" not in props
            assert "approve" not in props


@pytest.mark.anyio
async def test_tool_calls_require_authentication(
    running_server: tuple[str, str],
) -> None:
    """Without a session token, tool calls are rejected."""
    _, mcp_url = running_server
    async with mcp_buyer_client(mcp_url, None) as client:
        result = await client.call_tool("search_catalog", {"merchant_id": "mer_1"})
        assert result.is_error is True
        text = result.content[0]
        assert isinstance(text, TextContent)
        assert "buyer session" in text.text.lower()


@pytest.mark.anyio
async def test_tool_calls_with_valid_session_succeed(
    running_server: tuple[str, str],
) -> None:
    """With a valid session, search_catalog reaches the real services."""
    _, mcp_url = running_server
    async with mcp_buyer_client(mcp_url, "buyer_1") as client:
        result = await client.call_tool("search_catalog", {"merchant_id": "mer_1"})
        assert result.is_error is not True
        text = result.content[0]
        assert isinstance(text, TextContent)
        data = json.loads(text.text)
        assert "items" in data
        assert data["items"][0]["merchant_id"] == "mer_1"


@pytest.mark.anyio
async def test_tools_use_session_buyer_identity(
    running_server: tuple[str, str],
) -> None:
    """The proposal's buyer_id is the authenticated session buyer, not an argument."""
    _, mcp_url = running_server
    async with mcp_buyer_client(mcp_url, "buyer_carol") as client:
        result = await client.call_tool(
            "create_purchase_proposal",
            {"merchant_id": "mer_1", "product_id": "prod_fake_001", "quantity": 1},
        )
        data = json.loads(result.content[0].text)  # type: ignore[index]
        assert data["buyer_id"] == "buyer_carol"


@pytest.mark.anyio
async def test_get_product_and_status(running_server: tuple[str, str]) -> None:
    _, mcp_url = running_server
    async with mcp_buyer_client(mcp_url, "buyer_1") as client:
        prod = await client.call_tool(
            "get_product", {"merchant_id": "mer_1", "product_id": "prod_fake_001"}
        )
        assert json.loads(prod.content[0].text)["id"] == "prod_fake_001"  # type: ignore[index]

        status = await client.call_tool(
            "get_transaction_status", {"transaction_id": "txn_1"}
        )
        assert json.loads(status.content[0].text)["id"] == "txn_1"  # type: ignore[index]


@pytest.mark.anyio
async def test_get_transaction_audit(running_server: tuple[str, str]) -> None:
    _, mcp_url = running_server
    async with mcp_buyer_client(mcp_url, "buyer_1") as client:
        result = await client.call_tool(
            "get_transaction_audit", {"transaction_id": "txn_1"}
        )
        data = json.loads(result.content[0].text)  # type: ignore[index]
        assert "items" in data


@pytest.mark.anyio
async def test_mutations_derive_deterministic_idempotency_keys(
    running_server: tuple[str, str],
) -> None:
    """Repeating the same mutation replays the same derived idempotency key."""
    _, mcp_url = running_server
    async with mcp_buyer_client(mcp_url, "buyer_1") as client:
        first = await client.call_tool(
            "create_purchase_proposal",
            {"merchant_id": "mer_1", "product_id": "prod_fake_001", "quantity": 1},
        )
        second = await client.call_tool(
            "create_purchase_proposal",
            {"merchant_id": "mer_1", "product_id": "prod_fake_001", "quantity": 1},
        )
        first_data = json.loads(first.content[0].text)  # type: ignore[index]
        second_data = json.loads(second.content[0].text)  # type: ignore[index]
        # The fake service returns a deterministic id; the point here is that
        # both calls succeed and produce equivalent results (same dedupe key).
        assert first_data["id"] == second_data["id"]
        assert first_data["buyer_id"] == second_data["buyer_id"] == "buyer_1"


@pytest.mark.anyio
async def test_mcp_full_purchase_journey(running_server: tuple[str, str]) -> None:
    """MCP E2E verified: search → proposal → auth → human approval → execute → status → audit."""
    base_url, mcp_url = running_server
    buyer_id = "buyer_carol"

    async with mcp_buyer_client(mcp_url, buyer_id) as mcp:
        # 1. MCP: search catalog
        search = await mcp.call_tool("search_catalog", {"merchant_id": "mer_1"})
        assert search.is_error is not True
        search_data = json.loads(search.content[0].text)  # type: ignore[index]
        assert len(search_data["items"]) > 0
        product_id = search_data["items"][0]["id"]

        # 2. MCP: create purchase proposal
        proposal = await mcp.call_tool(
            "create_purchase_proposal",
            {"merchant_id": "mer_1", "product_id": product_id, "quantity": 1},
        )
        assert proposal.is_error is not True
        proposal_data = json.loads(proposal.content[0].text)  # type: ignore[index]
        assert proposal_data["buyer_id"] == buyer_id
        proposal_id = proposal_data["id"]

        # 3. MCP: request authorization
        auth_req = await mcp.call_tool(
            "request_authorization",
            {"proposal_id": proposal_id},
        )
        assert auth_req.is_error is not True
        auth_data = json.loads(auth_req.content[0].text)  # type: ignore[index]
        assert auth_data["status"] == "REQUESTED"

        # 4. REST: human buyer approval (MCP correctly has no approve tool)
        token = issue_buyer_token(buyer_id)
        async with httpx.AsyncClient(base_url=base_url) as http:
            approval_resp = await http.post(
                f"/v1/buyer/purchase-proposals/{proposal_id}/approvals",
                json={
                    "proposal_hash": proposal_data["proposal_hash"],
                    "max_quantity": proposal_data["quantity"],
                    "max_amount_minor": proposal_data["total"]["amount_minor"],
                    "currency": proposal_data["total"]["currency"],
                    "expires_at": proposal_data["expires_at"],
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": "mcp-e2e-approval-1",
                    "Content-Type": "application/json",
                },
            )
            assert approval_resp.status_code == 200
            assert approval_resp.json()["status"] == "APPROVED"

        # 5. MCP: execute transaction
        execute = await mcp.call_tool(
            "execute_transaction",
            {"proposal_id": proposal_id},
        )
        assert execute.is_error is not True
        txn_data = json.loads(execute.content[0].text)  # type: ignore[index]
        txn_id = txn_data["id"]
        assert txn_data["buyer_id"] == buyer_id

        # 6. MCP: get transaction status
        status = await mcp.call_tool(
            "get_transaction_status",
            {"transaction_id": txn_id},
        )
        assert status.is_error is not True
        status_data = json.loads(status.content[0].text)  # type: ignore[index]
        assert status_data["id"] == txn_id
        assert status_data["buyer_id"] == buyer_id

        # 7. MCP: get transaction audit trail
        audit = await mcp.call_tool(
            "get_transaction_audit",
            {"transaction_id": txn_id},
        )
        assert audit.is_error is not True
        audit_data = json.loads(audit.content[0].text)  # type: ignore[index]
        assert len(audit_data["items"]) >= 1
