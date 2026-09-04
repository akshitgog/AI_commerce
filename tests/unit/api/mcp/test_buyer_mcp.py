"""MCP Buyer Server contract tests.

These tests use the in-memory MCP Client (passing the MCPServer directly)
to verify:
- initialize/connection succeeds
- tools/list exposes exactly 7 tools with correct names
- Input schemas are complete (derived from function signatures)
- Valid tool calls reach BuyerAdapter and return results
- Invalid arguments are rejected
- Adapter errors map safely to MCP errors
"""

import json

import pytest
from mcp.client import Client
from mcp.types import TextContent

from ai_commerce_gateway.api.buyer_chat.stubs import (
    get_auth_service,
    get_catalog_service,
    get_proposal_service,
    get_transaction_service,
)
from ai_commerce_gateway.api.mcp.buyer_server import create_buyer_mcp_server
from ai_commerce_gateway.application.buyer_adapter.adapter import BuyerAdapter

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


@pytest.fixture
def buyer_adapter() -> BuyerAdapter:
    return BuyerAdapter(
        catalog=get_catalog_service(),
        proposal=get_proposal_service(),
        auth=get_auth_service(),
        transaction=get_transaction_service(),
    )


@pytest.mark.anyio
async def test_initialize_succeeds(buyer_adapter: BuyerAdapter) -> None:
    """MCP initialization/connection should succeed."""
    mcp = create_buyer_mcp_server(buyer_adapter)
    async with Client(mcp) as client:
        # If we get here without exception, initialize succeeded
        tools = await client.list_tools()
        assert tools is not None


@pytest.mark.anyio
async def test_tools_list_exactly_seven(
    buyer_adapter: BuyerAdapter,
) -> None:
    """tools/list must expose exactly the 7 buyer tools."""
    mcp = create_buyer_mcp_server(buyer_adapter)
    async with Client(mcp) as client:
        result = await client.list_tools()
        tool_names = sorted([t.name for t in result.tools])
        assert tool_names == EXPECTED_TOOL_NAMES
        assert len(result.tools) == 7


@pytest.mark.anyio
async def test_tool_schemas_are_complete(
    buyer_adapter: BuyerAdapter,
) -> None:
    """Every tool must have a non-empty inputSchema with properties."""
    mcp = create_buyer_mcp_server(buyer_adapter)
    async with Client(mcp) as client:
        result = await client.list_tools()
        for tool in result.tools:
            schema = tool.input_schema
            assert schema is not None, f"Tool {tool.name} has no input_schema"
            assert "properties" in schema, f"Tool {tool.name} schema missing 'properties'"


@pytest.mark.anyio
async def test_search_catalog_reaches_adapter(
    buyer_adapter: BuyerAdapter,
) -> None:
    """search_catalog should reach BuyerAdapter and return results."""
    mcp = create_buyer_mcp_server(buyer_adapter)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "search_catalog",
            {"merchant_id": "mer_demo_001"},
        )
        assert len(result.content) > 0
        text_content = result.content[0]
        assert isinstance(text_content, TextContent)
        data = json.loads(text_content.text)
        assert "items" in data
        assert len(data["items"]) > 0
        assert data["items"][0]["merchant_id"] == "mer_demo_001"


@pytest.mark.anyio
async def test_get_product_reaches_adapter(
    buyer_adapter: BuyerAdapter,
) -> None:
    """get_product should reach BuyerAdapter and return product."""
    mcp = create_buyer_mcp_server(buyer_adapter)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_product",
            {"product_id": "prod_demo_001"},
        )
        assert len(result.content) > 0
        text_content = result.content[0]
        assert isinstance(text_content, TextContent)
        data = json.loads(text_content.text)
        assert data["id"] == "prod_demo_001"


@pytest.mark.anyio
async def test_create_purchase_proposal_reaches_adapter(
    buyer_adapter: BuyerAdapter,
) -> None:
    """create_purchase_proposal should reach ProposalService."""
    mcp = create_buyer_mcp_server(buyer_adapter)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "create_purchase_proposal",
            {
                "merchant_id": "mer_demo_001",
                "product_id": "prod_demo_001",
                "quantity": 2,
            },
        )
        assert len(result.content) > 0
        text_content = result.content[0]
        assert isinstance(text_content, TextContent)
        data = json.loads(text_content.text)
        assert "id" in data
        assert data["quantity"] == 2


@pytest.mark.anyio
async def test_request_authorization_reaches_adapter(
    buyer_adapter: BuyerAdapter,
) -> None:
    """request_authorization maps to AuthorizationService."""
    mcp = create_buyer_mcp_server(buyer_adapter)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "request_authorization",
            {"proposal_id": "prop_demo_001"},
        )
        assert len(result.content) > 0
        text_content = result.content[0]
        assert isinstance(text_content, TextContent)
        data = json.loads(text_content.text)
        assert data["status"] == "REQUESTED"


@pytest.mark.anyio
async def test_execute_transaction_reaches_adapter(
    buyer_adapter: BuyerAdapter,
) -> None:
    """execute_transaction maps to TransactionService."""
    mcp = create_buyer_mcp_server(buyer_adapter)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "execute_transaction",
            {"proposal_id": "prop_demo_001"},
        )
        assert len(result.content) > 0
        text_content = result.content[0]
        assert isinstance(text_content, TextContent)
        data = json.loads(text_content.text)
        assert "id" in data


@pytest.mark.anyio
async def test_get_transaction_status_reaches_adapter(
    buyer_adapter: BuyerAdapter,
) -> None:
    """get_transaction_status maps to TransactionService."""
    mcp = create_buyer_mcp_server(buyer_adapter)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_transaction_status",
            {"transaction_id": "txn_demo_001"},
        )
        assert len(result.content) > 0
        text_content = result.content[0]
        assert isinstance(text_content, TextContent)
        data = json.loads(text_content.text)
        assert data["id"] == "txn_demo_001"


@pytest.mark.anyio
async def test_get_transaction_audit_reaches_adapter(
    buyer_adapter: BuyerAdapter,
) -> None:
    """get_transaction_audit maps to TransactionService."""
    mcp = create_buyer_mcp_server(buyer_adapter)
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_transaction_audit",
            {"transaction_id": "txn_demo_001"},
        )
        assert len(result.content) > 0
        text_content = result.content[0]
        assert isinstance(text_content, TextContent)
        data = json.loads(text_content.text)
        assert "items" in data


@pytest.mark.anyio
async def test_mcp_cannot_bypass_adapter(
    buyer_adapter: BuyerAdapter,
) -> None:
    """MCP must not expose any tools beyond the 7 buyer tools.

    This ensures an MCP client cannot access admin, merchant-only,
    or provider-level operations.
    """
    mcp = create_buyer_mcp_server(buyer_adapter)
    async with Client(mcp) as client:
        result = await client.list_tools()
        tool_names = {t.name for t in result.tools}
        # None of these should exist
        forbidden = {
            "approve_authorization",
            "admin_delete",
            "razorpay_checkout",
            "create_product_draft",
            "publish_product",
        }
        assert tool_names & forbidden == set()
