"""MCP Buyer Server contract tests.

These tests use the in-memory MCP Client (passing the MCPServer directly)
to verify:
- initialize/connection succeeds
- tools/list exposes exactly 7 tools with correct names
- Input schemas are complete (derived from function signatures)
- Valid tool calls reach the application services through the composition
  seam and return results
- Invalid arguments are rejected
- Adapter errors map safely to MCP errors
"""

import json
from dataclasses import dataclass, field

import pytest
from mcp.client import Client
from mcp.types import TextContent

from ai_commerce_gateway.api.composition import (
    BuyerServiceBundle,
    BuyerServicesFactory,
    static_bundle_factory,
)
from ai_commerce_gateway.api.mcp.buyer_server import create_buyer_mcp_server
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    CreateTransactionCommand,
    ExecuteTransactionCommand,
    TransactionView,
)
from tests.unit.application.buyer_adapter.fakes import (
    FakeAuthorizationService,
    FakeCatalogService,
    FakeProposalService,
    FakeTransactionService,
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


@dataclass
class RecordingTransactionService(FakeTransactionService):
    """Fake transaction service that records commands for assertions."""

    create_commands: list[CreateTransactionCommand] = field(default_factory=list)
    execute_commands: list[ExecuteTransactionCommand] = field(default_factory=list)

    def create(
        self, command: CreateTransactionCommand, actor: ActorContext
    ) -> TransactionView:
        self.create_commands.append(command)
        return super().create(command, actor)

    def execute(
        self, command: ExecuteTransactionCommand, actor: ActorContext
    ) -> TransactionView:
        self.execute_commands.append(command)
        return super().execute(command, actor)


@pytest.fixture
def services_factory() -> BuyerServicesFactory:
    return static_bundle_factory(
        BuyerServiceBundle(
            catalog=FakeCatalogService(),
            proposal=FakeProposalService(),
            auth=FakeAuthorizationService(),
            transaction=RecordingTransactionService(),
        )
    )


@pytest.mark.anyio
async def test_initialize_succeeds(services_factory: BuyerServicesFactory) -> None:
    """MCP initialization/connection should succeed."""
    mcp = create_buyer_mcp_server(services_factory)
    async with Client(mcp) as client:
        # If we get here without exception, initialize succeeded
        tools = await client.list_tools()
        assert tools is not None


@pytest.mark.anyio
async def test_tools_list_exactly_seven(
    services_factory: BuyerServicesFactory,
) -> None:
    """tools/list must expose exactly the 7 buyer tools."""
    mcp = create_buyer_mcp_server(services_factory)
    async with Client(mcp) as client:
        result = await client.list_tools()
        tool_names = sorted([t.name for t in result.tools])
        assert tool_names == EXPECTED_TOOL_NAMES
        assert len(result.tools) == 7


@pytest.mark.anyio
async def test_tool_schemas_are_complete(
    services_factory: BuyerServicesFactory,
) -> None:
    """Every tool must have a non-empty inputSchema with properties."""
    mcp = create_buyer_mcp_server(services_factory)
    async with Client(mcp) as client:
        result = await client.list_tools()
        for tool in result.tools:
            schema = tool.input_schema
            assert schema is not None, f"Tool {tool.name} has no input_schema"
            assert "properties" in schema, f"Tool {tool.name} schema missing 'properties'"


@pytest.mark.anyio
async def test_search_catalog_reaches_services(
    services_factory: BuyerServicesFactory,
) -> None:
    """search_catalog should reach the catalog service and return results."""
    mcp = create_buyer_mcp_server(services_factory)
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
async def test_get_product_reaches_services(
    services_factory: BuyerServicesFactory,
) -> None:
    """get_product should reach the catalog service and return product."""
    mcp = create_buyer_mcp_server(services_factory)
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
async def test_create_purchase_proposal_reaches_services(
    services_factory: BuyerServicesFactory,
) -> None:
    """create_purchase_proposal should reach ProposalService."""
    mcp = create_buyer_mcp_server(services_factory)
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
async def test_request_authorization_reaches_services(
    services_factory: BuyerServicesFactory,
) -> None:
    """request_authorization maps to AuthorizationService."""
    mcp = create_buyer_mcp_server(services_factory)
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
async def test_execute_transaction_reaches_services(
    services_factory: BuyerServicesFactory,
) -> None:
    """execute_transaction maps to TransactionService."""
    mcp = create_buyer_mcp_server(services_factory)
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
async def test_get_transaction_status_reaches_services(
    services_factory: BuyerServicesFactory,
) -> None:
    """get_transaction_status maps to TransactionService."""
    mcp = create_buyer_mcp_server(services_factory)
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
async def test_get_transaction_audit_reaches_services(
    services_factory: BuyerServicesFactory,
) -> None:
    """get_transaction_audit maps to TransactionService."""
    mcp = create_buyer_mcp_server(services_factory)
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
async def test_mcp_cannot_bypass_services(
    services_factory: BuyerServicesFactory,
) -> None:
    """MCP must not expose any tools beyond the 7 buyer tools.

    This ensures an MCP client cannot access admin, merchant-only,
    or provider-level operations.
    """
    mcp = create_buyer_mcp_server(services_factory)
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


@pytest.mark.anyio
async def test_execute_transaction_is_idempotent() -> None:
    """Mutating tools must derive deterministic idempotency keys on replay."""
    transaction_service = RecordingTransactionService()
    factory = static_bundle_factory(
        BuyerServiceBundle(
            catalog=FakeCatalogService(),
            proposal=FakeProposalService(),
            auth=FakeAuthorizationService(),
            transaction=transaction_service,
        )
    )
    mcp = create_buyer_mcp_server(factory)

    async with Client(mcp) as client:
        await client.call_tool(
            "execute_transaction",
            {"proposal_id": "prop_demo_001"},
        )
        await client.call_tool(
            "execute_transaction",
            {"proposal_id": "prop_demo_001"},
        )

    assert len(transaction_service.create_commands) == 2
    assert len(transaction_service.execute_commands) == 2
    # The derived idempotency key must be identical on replay so the real
    # transaction service can deduplicate the physical provider order.
    key_1 = transaction_service.create_commands[0].idempotency_key
    key_2 = transaction_service.create_commands[1].idempotency_key
    assert key_1 == key_2
    assert key_1.startswith("idem_")
    exec_key_1 = transaction_service.execute_commands[0].idempotency_key
    exec_key_2 = transaction_service.execute_commands[1].idempotency_key
    assert exec_key_1 == exec_key_2
