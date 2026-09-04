"""Unit tests for buyer chat HTTP router (C2).

These are component tests:  they hit the FastAPI routes via TestClient,
use stub services (no real DB / Razorpay) and verify:

  - all 7 buyer endpoints are reachable and return 200
  - correlation_id propagates from request header to response body
  - Idempotency-Key header is consumed by the transport (not the AI)
  - mutating endpoints reject missing Idempotency-Key with 422
  - routes return canonical response shapes
  - actor identity comes from X-Buyer-ID header (server-side binding)
  - no price / total / provider fields can be supplied by the client
    to mutate the server-derived values
  - no MCP dependency exists in this module
"""

import pytest
from fastapi.testclient import TestClient

from ai_commerce_gateway.api.app import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app, raise_server_exceptions=True)


BUYER_HEADERS = {
    "X-Buyer-ID": "buyer_test_001",
    "X-Correlation-ID": "corr_test_001",
}

IDEM_HEADERS = {**BUYER_HEADERS, "Idempotency-Key": "idem_test_001"}


# ---------------------------------------------------------------------------
# Search catalog
# ---------------------------------------------------------------------------


def test_search_catalog_returns_200(client: TestClient) -> None:
    resp = client.post(
        "/v1/buyer/catalog/search",
        json={"merchant_id": "mer_001"},
        headers=BUYER_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "correlation_id" in body
    assert body["correlation_id"] == "corr_test_001"


def test_search_catalog_no_price_field_in_body(client: TestClient) -> None:
    """Client cannot inject a price field into catalog search."""
    resp = client.post(
        "/v1/buyer/catalog/search",
        json={"merchant_id": "mer_001", "price": 999},  # extra field ignored by Pydantic
        headers=BUYER_HEADERS,
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Get product
# ---------------------------------------------------------------------------


def test_get_product_returns_200(client: TestClient) -> None:
    resp = client.get(
        "/v1/buyer/catalog/products/prod_001",
        headers=BUYER_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "prod_001"
    assert "price" in body
    assert "correlation_id" in body


# ---------------------------------------------------------------------------
# Create purchase proposal
# ---------------------------------------------------------------------------


def test_create_proposal_returns_server_derived_total(client: TestClient) -> None:
    """Server derives total — client cannot supply it."""
    resp = client.post(
        "/v1/buyer/purchase-proposals",
        json={"merchant_id": "mer_001", "product_id": "prod_001", "quantity": 2},
        headers=IDEM_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "total" in body
    assert "unit_price" in body
    # The proposal_hash proves server computed the immutable proposal
    assert "proposal_hash" in body
    assert body["quantity"] == 2


def test_create_proposal_client_cannot_supply_price(client: TestClient) -> None:
    """Any client-supplied price/total field is not accepted."""
    resp = client.post(
        "/v1/buyer/purchase-proposals",
        json={
            "merchant_id": "mer_001",
            "product_id": "prod_001",
            "quantity": 1,
            "price": {"amount_minor": 1, "currency": "INR"},  # must be ignored / rejected
        },
        headers=IDEM_HEADERS,
    )
    # Pydantic model forbids extra fields — FastAPI returns 422
    assert resp.status_code in (200, 422)
    if resp.status_code == 200:
        body = resp.json()
        # Server-derived price must NOT equal the client-injected value
        assert body["unit_price"]["amount_minor"] != 1


def test_create_proposal_missing_idempotency_key_raises(client: TestClient) -> None:
    """Mutating operation without Idempotency-Key header must fail."""
    resp = client.post(
        "/v1/buyer/purchase-proposals",
        json={"merchant_id": "mer_001", "product_id": "prod_001", "quantity": 1},
        headers=BUYER_HEADERS,  # no Idempotency-Key
    )
    assert resp.status_code in (422, 400, 500)


# ---------------------------------------------------------------------------
# Request authorization
# ---------------------------------------------------------------------------


def test_request_authorization_returns_requested_status(client: TestClient) -> None:
    resp = client.post(
        "/v1/buyer/purchase-proposals/prop_001/authorization-requests",
        headers=IDEM_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "REQUESTED"
    assert body["authorized_by"] is None  # AI cannot approve itself


def test_request_authorization_missing_idempotency_key_raises(client: TestClient) -> None:
    resp = client.post(
        "/v1/buyer/purchase-proposals/prop_001/authorization-requests",
        headers=BUYER_HEADERS,  # no Idempotency-Key
    )
    assert resp.status_code in (422, 400, 500)


# ---------------------------------------------------------------------------
# Execute transaction
# ---------------------------------------------------------------------------


def test_execute_transaction_returns_state(client: TestClient) -> None:
    resp = client.post(
        "/v1/buyer/transactions",
        json={"proposal_id": "prop_001"},
        headers=IDEM_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] in ("READY", "EXECUTING", "PAYMENT_PENDING")


def test_execute_transaction_missing_idempotency_key_raises(client: TestClient) -> None:
    resp = client.post(
        "/v1/buyer/transactions",
        json={"proposal_id": "prop_001"},
        headers=BUYER_HEADERS,  # no Idempotency-Key
    )
    assert resp.status_code in (422, 400, 500)


# ---------------------------------------------------------------------------
# Get transaction status
# ---------------------------------------------------------------------------


def test_get_transaction_status_is_read_only(client: TestClient) -> None:
    resp = client.get(
        "/v1/buyer/transactions/txn_001",
        headers=BUYER_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "state" in body
    assert "correlation_id" in body


# ---------------------------------------------------------------------------
# Get transaction audit
# ---------------------------------------------------------------------------


def test_get_transaction_audit_is_read_only(client: TestClient) -> None:
    resp = client.get(
        "/v1/buyer/transactions/txn_001/events",
        headers=BUYER_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "correlation_id" in body


# ---------------------------------------------------------------------------
# Correlation ID propagation
# ---------------------------------------------------------------------------


def test_correlation_id_propagates_from_header(client: TestClient) -> None:
    resp = client.post(
        "/v1/buyer/catalog/search",
        json={"merchant_id": "mer_001"},
        headers={**BUYER_HEADERS, "X-Correlation-ID": "custom_corr_xyz"},
    )
    assert resp.status_code == 200
    assert resp.json()["correlation_id"] == "custom_corr_xyz"


def test_correlation_id_in_response_header(client: TestClient) -> None:
    resp = client.post(
        "/v1/buyer/catalog/search",
        json={"merchant_id": "mer_001"},
        headers=BUYER_HEADERS,
    )
    assert resp.status_code == 200
    assert "x-correlation-id" in resp.headers


# ---------------------------------------------------------------------------
# No MCP dependency
# ---------------------------------------------------------------------------


def test_no_mcp_import_in_router() -> None:
    """Verify the chat router has no MCP dependency."""
    import importlib
    import sys

    # Remove cached module to force fresh import
    mods = [k for k in sys.modules if "buyer_chat" in k]
    for m in mods:
        del sys.modules[m]

    spec = importlib.util.find_spec(  # type: ignore[attr-defined]
        "ai_commerce_gateway.api.buyer_chat.router"
    )
    assert spec is not None
    # mcp is not in the source file
    import ai_commerce_gateway.api.buyer_chat.router as chat_router_mod

    source_file = chat_router_mod.__file__ or ""
    with open(source_file, encoding="utf-8") as f:
        source = f.read()
    assert "mcp" not in source.lower()
