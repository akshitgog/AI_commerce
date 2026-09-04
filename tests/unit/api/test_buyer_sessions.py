"""Buyer identity and session security tests (P0-3).

Proves that:
- buyer identity comes only from server-trusted HMAC session tokens;
- X-Buyer-ID, request bodies and query parameters can never set identity;
- tampered, expired, foreign-secret and unsigned tokens are rejected;
- session issuance is guarded by the configured issuer key;
- the human approve endpoint stays outside the AI/MCP surface and binds the
  approval to the authenticated session buyer.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from ai_commerce_gateway.api.app import create_app
from ai_commerce_gateway.api.composition import (
    BuyerServiceBundle,
    static_bundle_factory,
)
from ai_commerce_gateway.api.session_auth import BuyerSessionService
from ai_commerce_gateway.core.config import Settings
from tests.conftest import (
    TEST_ISSUER_KEY,
    TEST_SESSION_SECRET,
    fake_service_bundle,
    issue_buyer_token,
    test_settings,
)
from tests.unit.application.buyer_adapter.fakes import FakeAuthorizationService


@pytest.fixture
def app_client() -> TestClient:
    app = create_app(
        services_factory=static_bundle_factory(fake_service_bundle()),
        settings=test_settings(),
    )
    return TestClient(app, raise_server_exceptions=True)


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Session issuance
# ---------------------------------------------------------------------------


def test_issue_session_requires_issuer_key(app_client: TestClient) -> None:
    response = app_client.post(
        "/v1/buyer/sessions",
        json={"buyer_id": "buyer_1"},
        headers={"X-Session-Issuer-Key": TEST_ISSUER_KEY},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["buyer_id"] == "buyer_1"
    assert payload["session_token"]
    assert payload["expires_at"]


def test_issue_session_rejects_wrong_issuer_key(app_client: TestClient) -> None:
    response = app_client.post(
        "/v1/buyer/sessions",
        json={"buyer_id": "buyer_1"},
        headers={"X-Session-Issuer-Key": "wrong"},
    )
    assert response.status_code == 403


def test_issue_session_rejects_missing_issuer_key(app_client: TestClient) -> None:
    response = app_client.post(
        "/v1/buyer/sessions",
        json={"buyer_id": "buyer_1"},
    )
    assert response.status_code == 403


def test_issue_session_disabled_without_issuer_key() -> None:
    settings = Settings(
        buyer_sessions_secret=SecretStr(TEST_SESSION_SECRET),
        buyer_sessions_issuer_key=None,
    )
    app = create_app(
        services_factory=static_bundle_factory(fake_service_bundle()),
        settings=settings,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/buyer/sessions",
            json={"buyer_id": "buyer_1"},
            headers={"X-Session-Issuer-Key": "anything"},
        )
    assert response.status_code == 503


# ---------------------------------------------------------------------------
# Authentication: only server-signed tokens are accepted
# ---------------------------------------------------------------------------


def test_no_token_is_unauthenticated(app_client: TestClient) -> None:
    response = app_client.post(
        "/v1/buyer/catalog/search", json={"merchant_id": "mer_1"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_arbitrary_bearer_token_is_rejected(app_client: TestClient) -> None:
    response = app_client.post(
        "/v1/buyer/catalog/search",
        json={"merchant_id": "mer_1"},
        headers=_auth_headers("buyer_test_001"),
    )
    assert response.status_code == 401


def test_tampered_token_is_rejected(app_client: TestClient) -> None:
    token = issue_buyer_token("buyer_1")
    tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    response = app_client.post(
        "/v1/buyer/catalog/search",
        json={"merchant_id": "mer_1"},
        headers=_auth_headers(tampered),
    )
    assert response.status_code == 401


def test_expired_token_is_rejected() -> None:
    import time

    service = BuyerSessionService(
        secret=SecretStr(TEST_SESSION_SECRET), ttl_seconds=1
    )
    token, _claims = service.issue("buyer_1")
    assert service.resolve(token) is not None
    # itsdangerous compares integer timestamps, so expiry needs > 2s elapsed
    time.sleep(2.2)
    assert service.resolve(token) is None


def test_foreign_secret_token_is_rejected(app_client: TestClient) -> None:
    foreign = BuyerSessionService(
        secret=SecretStr("another-secret"), ttl_seconds=3600
    )
    token, _claims = foreign.issue("buyer_1")
    response = app_client.post(
        "/v1/buyer/catalog/search",
        json={"merchant_id": "mer_1"},
        headers=_auth_headers(token),
    )
    assert response.status_code == 401


def test_valid_token_authenticates(app_client: TestClient) -> None:
    response = app_client.post(
        "/v1/buyer/catalog/search",
        json={"merchant_id": "mer_1"},
        headers=_auth_headers(issue_buyer_token("buyer_1")),
    )
    assert response.status_code == 200


def test_missing_session_secret_fails_closed() -> None:
    settings = Settings(buyer_sessions_secret=None)
    app = create_app(
        services_factory=static_bundle_factory(fake_service_bundle()),
        settings=settings,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/v1/buyer/catalog/search",
            json={"merchant_id": "mer_1"},
            headers=_auth_headers(issue_buyer_token("buyer_1")),
        )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Ownership: identity can never come from the request
# ---------------------------------------------------------------------------


def test_x_buyer_id_header_is_never_trusted(app_client: TestClient) -> None:
    """An X-Buyer-ID header alone must not authenticate anyone."""
    response = app_client.post(
        "/v1/buyer/catalog/search",
        json={"merchant_id": "mer_1"},
        headers={"X-Buyer-ID": "buyer_evil"},
    )
    assert response.status_code == 401


def test_x_buyer_id_cannot_override_session_identity(app_client: TestClient) -> None:
    """With a valid session, a hostile X-Buyer-ID must not change identity."""
    response = app_client.post(
        "/v1/buyer/purchase-proposals",
        json={"merchant_id": "mer_1", "product_id": "prod_1", "quantity": 1},
        headers={
            **_auth_headers(issue_buyer_token("buyer_alice")),
            "Idempotency-Key": "idem_own_1",
            "X-Buyer-ID": "buyer_evil",
        },
    )
    assert response.status_code == 200
    assert response.json()["buyer_id"] == "buyer_alice"


def test_body_buyer_fields_cannot_override_session_identity(
    app_client: TestClient,
) -> None:
    """Buyer-spoofing fields in the body are ignored by the schema and the actor."""
    response = app_client.post(
        "/v1/buyer/purchase-proposals",
        json={
            "merchant_id": "mer_1",
            "product_id": "prod_1",
            "quantity": 1,
            "buyer_id": "buyer_evil",
            "actor_id": "buyer_evil",
        },
        headers={
            **_auth_headers(issue_buyer_token("buyer_alice")),
            "Idempotency-Key": "idem_own_2",
        },
    )
    assert response.status_code == 200
    assert response.json()["buyer_id"] == "buyer_alice"


def test_buyer_identity_scopes_mutations(app_client: TestClient) -> None:
    """Proposals for two different session buyers keep their own identities."""
    for buyer in ("buyer_alice", "buyer_bob"):
        response = app_client.post(
            "/v1/buyer/purchase-proposals",
            json={"merchant_id": "mer_1", "product_id": "prod_1", "quantity": 1},
            headers={
                **_auth_headers(issue_buyer_token(buyer)),
                "Idempotency-Key": f"idem_{buyer}",
            },
        )
        assert response.status_code == 200
        assert response.json()["buyer_id"] == buyer


# ---------------------------------------------------------------------------
# Human approval endpoint: outside the AI/MCP tool surface
# ---------------------------------------------------------------------------


def test_approve_endpoint_is_human_only_and_session_bound(
    app_client: TestClient,
) -> None:
    auth_service = FakeAuthorizationService()
    bundle = BuyerServiceBundle(
        catalog=fake_service_bundle().catalog,
        proposal=fake_service_bundle().proposal,
        auth=auth_service,
        transaction=fake_service_bundle().transaction,
    )
    app = create_app(
        services_factory=static_bundle_factory(bundle),
        settings=test_settings(),
    )
    expires = (datetime.now(UTC) + timedelta(minutes=15)).isoformat()

    with TestClient(app, raise_server_exceptions=True) as client:
        response = client.post(
            "/v1/buyer/purchase-proposals/prop_1/approvals",
            json={
                "proposal_hash": "hash_1",
                "max_quantity": 2,
                "max_amount_minor": 339800,
                "currency": "INR",
                "expires_at": expires,
            },
            headers={
                **_auth_headers(issue_buyer_token("buyer_alice")),
                "Idempotency-Key": "idem_approve_1",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "APPROVED"
    assert payload["buyer_id"] == "buyer_alice"
    assert payload["authorized_by"] == "buyer_alice"
    # The command reached the auth service exactly once, bound to the session buyer
    assert len(auth_service.approve_calls) == 1
    command = auth_service.approve_calls[0]
    assert command.proposal_id == "prop_1"
    assert command.max_amount.amount_minor == 339800
    assert command.max_amount.currency == "INR"
    assert command.idempotency_key == "idem_approve_1"


def test_approve_endpoint_requires_authentication(app_client: TestClient) -> None:
    expires = (datetime.now(UTC) + timedelta(minutes=15)).isoformat()
    response = app_client.post(
        "/v1/buyer/purchase-proposals/prop_1/approvals",
        json={
            "proposal_hash": "hash_1",
            "max_quantity": 1,
            "max_amount_minor": 1000,
            "currency": "INR",
            "expires_at": expires,
        },
        headers={"Idempotency-Key": "idem_approve_2"},
    )
    assert response.status_code == 401


def test_approve_endpoint_requires_idempotency_key(app_client: TestClient) -> None:
    expires = (datetime.now(UTC) + timedelta(minutes=15)).isoformat()
    response = app_client.post(
        "/v1/buyer/purchase-proposals/prop_1/approvals",
        json={
            "proposal_hash": "hash_1",
            "max_quantity": 1,
            "max_amount_minor": 1000,
            "currency": "INR",
            "expires_at": expires,
        },
        headers=_auth_headers(issue_buyer_token("buyer_alice")),
    )
    assert response.status_code == 422


def test_approve_is_not_on_the_ai_or_mcp_adapter() -> None:
    """The AI/MCP-facing BuyerAdapter must not expose an approve capability."""
    from ai_commerce_gateway.application.buyer_adapter.adapter import BuyerAdapter

    assert not hasattr(BuyerAdapter, "approve")
    assert not hasattr(BuyerAdapter, "approve_authorization")
    adapter_members = {name for name in dir(BuyerAdapter) if not name.startswith("_")}
    assert not any("approve" in name for name in adapter_members)
