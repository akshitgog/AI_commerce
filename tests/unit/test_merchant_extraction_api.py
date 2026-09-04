"""D-010 extraction endpoint tests: propose-only, tenant-scoped, role-gated."""


import pytest
from fastapi.testclient import TestClient

from ai_commerce_gateway.api.app import create_app
from ai_commerce_gateway.api.merchant import router as merchant_router_module


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """App with the extractor forced to the stub (no network, no API key)."""
    monkeypatch.setattr(
        merchant_router_module,
        "get_product_draft_extractor",
        lambda: merchant_router_module.StubProductDraftExtractor(),
    )
    app = create_app()
    return TestClient(app)


HEADERS = {
    "X-Merchant-User-ID": "mer_user_1",
    "X-Merchant-Roles": "ADMIN",
}

URL = "/merchants/mer_demo_1/products/extract-draft"


def test_extract_draft_returns_persisted_false(client: TestClient):
    res = client.post(
        URL,
        json={"text": "65W GaN Fast Charger. Price is ₹1,699 and I have 25 units."},
        headers=HEADERS,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["persisted"] is False
    draft = body["draft"]
    assert draft["title"] == "65W GaN Fast Charger"
    assert draft["price_amount_minor"] == 169900
    assert draft["available_quantity"] == 25
    assert draft["source"] == "stub"


def test_extract_draft_never_persists(client: TestClient):
    """Structural propose-only guarantee: no repository/session parameters."""
    import inspect

    from ai_commerce_gateway.api.merchant import router as router_module

    params = set(inspect.signature(router_module.extract_product_draft).parameters)
    assert params == {
        "merchant_id",
        "request",
        "extractor",
        "x_merchant_user_id",
        "x_merchant_roles",
    }


def test_extract_draft_empty_text_400(client: TestClient):
    res = client.post(URL, json={"text": "   "}, headers=HEADERS)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_extract_draft_viewer_role_403(client: TestClient):
    res = client.post(
        URL,
        json={"text": "A wooden stool"},
        headers={"X-Merchant-User-ID": "u1", "X-Merchant-Roles": "VIEWER"},
    )
    assert res.status_code == 403


def test_extract_draft_defaults_to_admin_demo_role(client: TestClient):
    res = client.post(URL, json={"text": "A wooden stool"})
    assert res.status_code == 200


def test_extract_draft_rejects_oversized_text(client: TestClient):
    res = client.post(URL, json={"text": "x" * 4001}, headers=HEADERS)
    assert res.status_code == 422  # pydantic max_length guard
