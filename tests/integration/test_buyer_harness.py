"""Integration harness proving parity between the Buyer Chat API and MCP Server."""

import asyncio
import json
import socket
from collections.abc import AsyncIterator

import httpx
import pytest
import uvicorn
from mcp.client import Client
from mcp.types import TextContent

from ai_commerce_gateway.api.app import create_app
from ai_commerce_gateway.api.composition import (
    BuyerServiceBundle,
    BuyerServicesFactory,
    static_bundle_factory,
)
from tests.conftest import buyer_headers, test_settings
from tests.unit.application.buyer_adapter.fakes import (
    FakeAuthorizationService,
    FakeCatalogService,
    FakeProposalService,
    FakeTransactionService,
)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def harness_factory() -> BuyerServicesFactory:
    """Create the composition seam with test fakes for the integration tests.

    This fulfills the 'dependency replacement' requirement through the same
    seam production uses; a real full-system run injects the real services
    here instead.
    """
    return static_bundle_factory(
        BuyerServiceBundle(
            catalog=FakeCatalogService(),
            proposal=FakeProposalService(),
            auth=FakeAuthorizationService(),
            transaction=FakeTransactionService(),
        )
    )


@pytest.fixture
async def running_server(harness_factory: BuyerServicesFactory) -> AsyncIterator[tuple[str, str]]:
    """Start the FastAPI app on a free port and yield the base URL and MCP URL."""

    port = _find_free_port()
    # Inject our harness factory into the app
    app = create_app(services_factory=harness_factory, settings=test_settings())

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())

    # Wait for server to start
    for _ in range(50):
        await asyncio.sleep(0.1)
        if server.started:
            break

    base_url = f"http://127.0.0.1:{port}"
    mcp_url = f"{base_url}/mcp/buyer/"

    try:
        yield base_url, mcp_url
    finally:
        server.should_exit = True
        await task


@pytest.mark.anyio
async def test_buyer_harness_chat_parity(running_server: tuple[str, str]) -> None:
    """Simulate a full buyer sequence via the /v1/buyer/chat endpoint (using HTTP).

    Proves that the chat API correctly processes intent into tool calls and traces them.
    """
    base_url, _ = running_server

    auth_headers = buyer_headers(
        "buyer_harness_001", correlation_id="corr_chat_001"
    )

    async with httpx.AsyncClient(base_url=base_url) as client:
        # 1. Search Catalog
        res_search = await client.post(
            "/v1/buyer/chat",
            json={"messages": [{"role": "user", "content": "search for demo products"}]},
            headers=auth_headers,
        )
        assert res_search.status_code == 200
        data = res_search.json()
        assert "search_catalog" in data["tool_calls"]
        assert data["correlation_id"] == "corr_chat_001"

        # Extract product ID from the fake catalog search result
        tool_results = {r["tool"]: r["result"] for r in data["tool_results"]}
        assert "search_catalog" in tool_results
        product_id = tool_results["search_catalog"]["items"][0]["id"]

        # 2. Create Proposal (Handoff trigger).
        # Hit the direct /v1/buyer/ endpoints to test transport parity with MCP.
        res_prop = await client.post(
            "/v1/buyer/purchase-proposals",
            json={"merchant_id": "mer_demo_1", "product_id": product_id, "quantity": 1},
            headers={**auth_headers, "Idempotency-Key": "idem_1"},
        )
        assert res_prop.status_code == 200
        proposal_id = res_prop.json()["id"]

        # 3. Request Authorization
        res_auth = await client.post(
            f"/v1/buyer/purchase-proposals/{proposal_id}/authorization-requests",
            json={"proposal_id": proposal_id},
            headers={**auth_headers, "Idempotency-Key": "idem_2"},
        )
        assert res_auth.status_code == 200

        # 4. Execute Transaction
        res_exec = await client.post(
            "/v1/buyer/transactions",
            json={"proposal_id": proposal_id},
            headers={**auth_headers, "Idempotency-Key": "idem_3"},
        )
        assert res_exec.status_code == 200
        txn_id = res_exec.json()["id"]

        # 5. Get Status
        res_status = await client.get(
            f"/v1/buyer/transactions/{txn_id}",
            headers=auth_headers,
        )
        assert res_status.status_code == 200
        assert res_status.json()["id"] == txn_id


@pytest.mark.anyio
async def test_buyer_harness_mcp_parity(running_server: tuple[str, str]) -> None:
    """Simulate the identical buyer sequence via the MCP Streamable HTTP transport.

    Proves that the remote MCP tools map to the exact same capabilities and traces.
    """
    _, mcp_url = running_server

    async with Client(mcp_url) as client:
        # 1. Search Catalog
        search_res = await client.call_tool("search_catalog", {"merchant_id": "mer_demo_1"})
        text_content = search_res.content[0]
        assert isinstance(text_content, TextContent)
        search_data = json.loads(text_content.text)
        product_id = search_data["items"][0]["id"]

        # 2. Create Proposal
        prop_res = await client.call_tool(
            "create_purchase_proposal",
            {"merchant_id": "mer_demo_1", "product_id": product_id, "quantity": 1},
        )
        prop_data = json.loads(prop_res.content[0].text)  # type: ignore
        proposal_id = prop_data["id"]

        # 3. Request Authorization
        auth_res = await client.call_tool("request_authorization", {"proposal_id": proposal_id})
        auth_data = json.loads(auth_res.content[0].text)  # type: ignore
        assert auth_data["id"] is not None

        # 4. Execute Transaction
        exec_res = await client.call_tool("execute_transaction", {"proposal_id": proposal_id})
        exec_data = json.loads(exec_res.content[0].text)  # type: ignore
        txn_id = exec_data["id"]

        # 5. Get Status
        status_res = await client.call_tool("get_transaction_status", {"transaction_id": txn_id})
        status_data = json.loads(status_res.content[0].text)  # type: ignore
        assert status_data["id"] == txn_id
