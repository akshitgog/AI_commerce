from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

import httpx
import pytest
from fastapi.testclient import TestClient
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client
from pydantic import SecretStr

from ai_commerce_gateway.api.app import create_app
from ai_commerce_gateway.api.composition import (
    BuyerServiceBundle,
    static_bundle_factory,
)
from ai_commerce_gateway.api.session_auth import BuyerSessionService
from ai_commerce_gateway.core.config import Settings, get_settings
from tests.unit.application.buyer_adapter.fakes import (
    FakeAuthorizationService,
    FakeCatalogService,
    FakeProposalService,
    FakeTransactionService,
)

TEST_SESSION_SECRET = "test-buyer-session-secret"
TEST_ISSUER_KEY = "test-buyer-session-issuer-key"


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def make_test_settings() -> Settings:
    """Settings for the buyer app under test, with session auth enabled."""
    return Settings(
        buyer_sessions_secret=SecretStr(TEST_SESSION_SECRET),
        buyer_sessions_issuer_key=SecretStr(TEST_ISSUER_KEY),
    )


def issue_buyer_token(buyer_id: str) -> str:
    """Mint a real buyer session token for tests (server-side operation)."""
    service = BuyerSessionService(
        secret=SecretStr(TEST_SESSION_SECRET),
        ttl_seconds=3600,
    )
    token, _claims = service.issue(buyer_id)
    return token


def buyer_headers(
    buyer_id: str, *, correlation_id: str | None = None
) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {issue_buyer_token(buyer_id)}"}
    if correlation_id is not None:
        headers["X-Correlation-ID"] = correlation_id
    return headers


@asynccontextmanager
async def mcp_buyer_client(
    mcp_url: str, buyer_id: str | None
) -> AsyncIterator[Client]:
    """Open an MCP client over Streamable HTTP with a real buyer session.

    ``buyer_id=None`` connects WITHOUT a session (for negative auth tests).
    """
    headers: dict[str, str] = {}
    if buyer_id is not None:
        headers["Authorization"] = f"Bearer {issue_buyer_token(buyer_id)}"
    http_client = httpx.AsyncClient(headers=headers)
    transport = streamable_http_client(mcp_url, http_client=http_client)
    client = Client(transport)
    async with client:
        yield client
    await http_client.aclose()


def fake_service_bundle() -> BuyerServiceBundle:
    """Test-only service bundle (fakes are permitted exclusively in tests)."""
    return BuyerServiceBundle(
        catalog=FakeCatalogService(),
        proposal=FakeProposalService(),
        auth=FakeAuthorizationService(),
        transaction=FakeTransactionService(),
    )


@pytest.fixture
def client() -> TestClient:
    """App client wired to test fakes through the real composition seam."""
    app = create_app(
        services_factory=static_bundle_factory(fake_service_bundle()),
        settings=make_test_settings(),
    )
    return TestClient(app, raise_server_exceptions=True)
