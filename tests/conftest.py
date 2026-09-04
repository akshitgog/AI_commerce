from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ai_commerce_gateway.api.app import create_app
from ai_commerce_gateway.api.composition import (
    BuyerServiceBundle,
    static_bundle_factory,
)
from ai_commerce_gateway.core.config import get_settings
from tests.unit.application.buyer_adapter.fakes import (
    FakeAuthorizationService,
    FakeCatalogService,
    FakeProposalService,
    FakeTransactionService,
)


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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
    app = create_app(services_factory=static_bundle_factory(fake_service_bundle()))
    return TestClient(app, raise_server_exceptions=True)
