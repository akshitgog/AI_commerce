"""P0 merchant API end-to-end tests (in-memory DB, session-authenticated).

Acceptance journey: conversational draft → review → save authoritative values
→ product stays DRAFT → human-confirmed publication → discoverable state,
with tenant/role, money, stale-version, idempotency and token defenses.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ai_commerce_gateway.api.app import create_app
from ai_commerce_gateway.api.merchant.router import get_db_session
from ai_commerce_gateway.domain.enums import MerchantRole
from ai_commerce_gateway.domain.merchant import AddMerchantUserDomain, CreateMerchantDomain
from ai_commerce_gateway.infrastructure.database.merchant_repositories import (
    SqlAlchemyMerchantRepository,
    SqlAlchemyMerchantUserRepository,
)
from ai_commerce_gateway.infrastructure.database import models
from ai_commerce_gateway.infrastructure.database.models import Base


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db() -> Iterator[Session]:
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = create_app()
    app.state.session_factory = factory
    app.dependency_overrides[get_db_session] = override_db

    seed = factory()
    SqlAlchemyMerchantRepository(seed).add(
        CreateMerchantDomain(id="mer_1", name="Demo Merchant", idempotency_key="ik_seed_m")
    )
    SqlAlchemyMerchantRepository(seed).add(
        CreateMerchantDomain(id="mer_2", name="Other Merchant", idempotency_key="ik_seed_m2")
    )
    users = SqlAlchemyMerchantUserRepository(seed)
    users.add(
        AddMerchantUserDomain(
            id="mu_admin", merchant_id="mer_1", user_id="user_admin", role=MerchantRole.ADMIN
        )
    )
    users.add(
        AddMerchantUserDomain(
            id="mu_viewer", merchant_id="mer_1", user_id="user_viewer", role=MerchantRole.VIEWER
        )
    )
    seed.commit()
    seed.close()

    yield TestClient(app)
    engine.dispose()


def _token(client: TestClient, user_id: str, merchant_id: str = "mer_1") -> str:
    res = client.post(f"/merchants/{merchant_id}/sessions", json={"user_id": user_id})
    assert res.status_code == 201, res.text
    return res.json()["session_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_transaction(client: TestClient) -> None:
    now = datetime.now(UTC)
    factory = client.app.state.session_factory
    with factory() as session:
        session.add_all(
            [
                models.Buyer(
                    id="buyer_1",
                    external_identity="buyer-one",
                    status="ACTIVE",
                ),
                models.Product(
                    id="prod_txn",
                    merchant_id="mer_1",
                    sku="TXN-SKU",
                    title="Audited product",
                    description="Used by merchant transaction route tests",
                    category="Tests",
                    price_minor=120000,
                    currency="INR",
                    available_quantity=5,
                    status="PUBLISHED",
                    version=1,
                ),
                models.PurchaseProposal(
                    id="prop_txn",
                    buyer_id="buyer_1",
                    merchant_id="mer_1",
                    product_id="prod_txn",
                    product_version=1,
                    quantity=1,
                    unit_price_minor=120000,
                    total_minor=120000,
                    currency="INR",
                    proposal_hash="proposal-hash-txn",
                    status="ACCEPTED",
                    expires_at=now + timedelta(minutes=10),
                ),
                models.Transaction(
                    id="txn_1",
                    proposal_id="prop_txn",
                    buyer_authorization_id=None,
                    merchant_decision_id=None,
                    merchant_id="mer_1",
                    buyer_id="buyer_1",
                    amount_minor=120000,
                    currency="INR",
                    state="UNKNOWN",
                ),
                models.TransactionEvent(
                    id="evt_1",
                    transaction_id="txn_1",
                    event_type="PROVIDER_OUTCOME_UNKNOWN",
                    actor_type="SYSTEM",
                    actor_id="payment-worker",
                    reason_code="PROVIDER_TIMEOUT",
                    previous_state="EXECUTING",
                    new_state="UNKNOWN",
                    correlation_id="corr_merchant_audit",
                    provider_reference_redacted="order_***1234",
                    metadata_json={"safe": "visible"},
                ),
            ]
        )
        session.commit()


def _create_product(
    client: TestClient, token: str, *, sku: str = "SKU-1", key: str = "ik_p1"
) -> dict:
    res = client.post(
        "/merchants/mer_1/products",
        json={
            "sku": sku,
            "title": "65W GaN Charger",
            "description": "Compact fast charger",
            "category": "Chargers",
            "price": {"amount_minor": 169900, "currency": "INR"},
            "available_quantity": 25,
            "idempotency_key": key,
        },
        headers=_auth(token),
    )
    assert res.status_code == 201, res.text
    return res.json()


def _issue_confirmation(
    client: TestClient, token: str, product_id: str, *, version: int, action: str
) -> str:
    res = client.post(
        f"/merchants/mer_1/products/{product_id}/publication-confirmations",
        json={"expected_version": version, "action": action},
        headers=_auth(token),
    )
    assert res.status_code == 200, res.text
    return res.json()["confirmation_token"]


class TestProductLifecycle:
    def test_create_is_draft_then_confirmed_publish(self, client: TestClient):
        token = _token(client, "user_admin")

        # DRAFT by default — the API never auto-publishes.
        product = _create_product(client, token)
        assert product["status"] == "DRAFT"
        assert product["version"] == 1
        assert product["price"]["amount_minor"] == 169900

        product_id = product["id"]

        # Reads work.
        res = client.get(f"/merchants/mer_1/products/{product_id}", headers=_auth(token))
        assert res.status_code == 200
        res = client.get("/merchants/mer_1/products", headers=_auth(token))
        assert any(p["id"] == product_id for p in res.json()["items"])

        # Publication requires a dashboard confirmation token.
        res = client.post(
            f"/merchants/mer_1/products/{product_id}/publish",
            json={"expected_version": 1, "idempotency_key": "ik_pub1"},
            headers=_auth(token),
        )
        assert res.status_code == 422  # confirmation_token required

        confirm_token = _issue_confirmation(
            client, token, product_id, version=1, action="PUBLISH"
        )
        res = client.post(
            f"/merchants/mer_1/products/{product_id}/publish",
            json={
                "expected_version": 1,
                "idempotency_key": "ik_pub1",
                "confirmation_token": confirm_token,
            },
            headers=_auth(token),
        )
        assert res.status_code == 200, res.text
        published = res.json()
        assert published["status"] == "PUBLISHED"
        assert published["version"] == 2

    def test_unpublish_with_confirmation(self, client: TestClient):
        token = _token(client, "user_admin")
        product = _create_product(client, token)
        product_id = product["id"]

        confirm = _issue_confirmation(client, token, product_id, version=1, action="PUBLISH")
        client.post(
            f"/merchants/mer_1/products/{product_id}/publish",
            json={
                "expected_version": 1,
                "idempotency_key": "ik_pub",
                "confirmation_token": confirm,
            },
            headers=_auth(token),
        )

        unconfirm = _issue_confirmation(
            client, token, product_id, version=2, action="UNPUBLISH"
        )
        res = client.post(
            f"/merchants/mer_1/products/{product_id}/unpublish",
            json={
                "expected_version": 2,
                "idempotency_key": "ik_unpub",
                "confirmation_token": unconfirm,
            },
            headers=_auth(token),
        )
        assert res.status_code == 200
        assert res.json()["status"] == "UNPUBLISHED"


class TestConfirmationTokenDefenses:
    def test_replay_rejected(self, client: TestClient):
        token = _token(client, "user_admin")
        product = _create_product(client, token)
        product_id = product["id"]
        confirm = _issue_confirmation(client, token, product_id, version=1, action="PUBLISH")

        first = client.post(
            f"/merchants/mer_1/products/{product_id}/publish",
            json={
                "expected_version": 1,
                "idempotency_key": "ik_pub",
                "confirmation_token": confirm,
            },
            headers=_auth(token),
        )
        assert first.status_code == 200

        replay = client.post(
            f"/merchants/mer_1/products/{product_id}/publish",
            json={
                "expected_version": 1,
                "idempotency_key": "ik_pub_replay",
                "confirmation_token": confirm,
            },
            headers=_auth(token),
        )
        assert replay.status_code == 409

    def test_version_drift_invalidates_token(self, client: TestClient):
        token = _token(client, "user_admin")
        product = _create_product(client, token)
        product_id = product["id"]

        confirm_v1 = _issue_confirmation(client, token, product_id, version=1, action="PUBLISH")
        client.post(
            f"/merchants/mer_1/products/{product_id}/publish",
            json={
                "expected_version": 1,
                "idempotency_key": "ik_pub",
                "confirmation_token": confirm_v1,
            },
            headers=_auth(token),
        )

        # A stale token bound to version 1 can never publish version 2.
        stale = _issue_confirmation(client, token, product_id, version=1, action="PUBLISH")
        res = client.post(
            f"/merchants/mer_1/products/{product_id}/publish",
            json={
                "expected_version": 1,
                "idempotency_key": "ik_pub_stale",
                "confirmation_token": stale,
            },
            headers=_auth(token),
        )
        assert res.status_code == 409

    def test_wrong_action_token_rejected(self, client: TestClient):
        token = _token(client, "user_admin")
        product = _create_product(client, token)
        product_id = product["id"]

        unpub_token = _issue_confirmation(
            client, token, product_id, version=1, action="UNPUBLISH"
        )
        res = client.post(
            f"/merchants/mer_1/products/{product_id}/publish",
            json={
                "expected_version": 1,
                "idempotency_key": "ik_pub",
                "confirmation_token": unpub_token,
            },
            headers=_auth(token),
        )
        assert res.status_code == 400

    def test_tampered_token_rejected(self, client: TestClient):
        token = _token(client, "user_admin")
        product = _create_product(client, token)
        product_id = product["id"]
        confirm = _issue_confirmation(client, token, product_id, version=1, action="PUBLISH")
        tampered = confirm[:-2] + ("AA" if not confirm.endswith("AA") else "BB")

        res = client.post(
            f"/merchants/mer_1/products/{product_id}/publish",
            json={
                "expected_version": 1,
                "idempotency_key": "ik_pub",
                "confirmation_token": tampered,
            },
            headers=_auth(token),
        )
        assert res.status_code == 400

    def test_mcp_credentials_cannot_mint_tokens(self, client: TestClient):
        """No session → no issuance. The MCP adapter only verifies."""
        res = client.post(
            "/merchants/mer_1/products/prod_x/publication-confirmations",
            json={"expected_version": 1, "action": "PUBLISH"},
        )
        assert res.status_code == 401


class TestMutationDefenses:
    def test_idempotency_replay_same_key(self, client: TestClient):
        token = _token(client, "user_admin")
        first = _create_product(client, token, key="ik_same")
        second = _create_product(client, token, key="ik_same")
        assert first["id"] == second["id"]

    def test_idempotency_different_fingerprint_rejected(self, client: TestClient):
        token = _token(client, "user_admin")
        _create_product(client, token, sku="SKU-A", key="ik_reuse")
        res = client.post(
            "/merchants/mer_1/products",
            json={
                "sku": "SKU-B",
                "title": "Different product",
                "description": "d",
                "price": {"amount_minor": 100, "currency": "INR"},
                "available_quantity": 1,
                "idempotency_key": "ik_reuse",
            },
            headers=_auth(token),
        )
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"

    def test_stale_version_update_rejected(self, client: TestClient):
        token = _token(client, "user_admin")
        product = _create_product(client, token)
        res = client.patch(
            f"/merchants/mer_1/products/{product['id']}",
            json={"expected_version": 99, "idempotency_key": "ik_upd", "title": "New"},
            headers=_auth(token),
        )
        assert res.status_code == 409

    @pytest.mark.parametrize(
        "bad_price",
        [
            {"amount_minor": True, "currency": "INR"},
            {"amount_minor": 1699.0, "currency": "INR"},
            {"amount_minor": "169900", "currency": "INR"},
            {"amount_minor": -1, "currency": "INR"},
            {"amount_minor": 100, "currency": "inr"},
        ],
    )
    def test_money_rejected_via_api(self, client: TestClient, bad_price: dict):
        token = _token(client, "user_admin")
        res = client.post(
            "/merchants/mer_1/products",
            json={
                "sku": "SKU-M",
                "title": "T",
                "description": "d",
                "price": bad_price,
                "available_quantity": 1,
                "idempotency_key": "ik_money",
            },
            headers=_auth(token),
        )
        assert res.status_code == 422

    def test_viewer_cannot_create(self, client: TestClient):
        token = _token(client, "user_viewer")
        res = client.post(
            "/merchants/mer_1/products",
            json={
                "sku": "SKU-V",
                "title": "T",
                "description": "d",
                "price": {"amount_minor": 100, "currency": "INR"},
                "available_quantity": 1,
                "idempotency_key": "ik_v",
            },
            headers=_auth(token),
        )
        assert res.status_code == 403

    def test_cross_tenant_denied(self, client: TestClient):
        token = _token(client, "user_admin")  # mer_1 session
        res = client.get("/merchants/mer_2/products", headers=_auth(token))
        assert res.status_code == 403


class TestPolicyAndReviewRoutes:
    def test_policy_update_then_read(self, client: TestClient):
        token = _token(client, "user_admin")
        res = client.put(
            "/merchants/mer_1/policy",
            json={"mode": "DENY_ALL", "idempotency_key": "ik_pol1"},
            headers=_auth(token),
        )
        assert res.status_code == 200, res.text
        assert res.json()["mode"] == "DENY_ALL"

        res = client.get("/merchants/mer_1/policy", headers=_auth(token))
        assert res.status_code == 200
        assert res.json()["mode"] == "DENY_ALL"

    def test_policy_viewer_cannot_update(self, client: TestClient):
        token = _token(client, "user_viewer")
        res = client.put(
            "/merchants/mer_1/policy",
            json={"mode": "DENY_ALL", "idempotency_key": "ik_pol"},
            headers=_auth(token),
        )
        assert res.status_code == 403

    def test_reviews_list_empty(self, client: TestClient):
        token = _token(client, "user_admin")
        res = client.get("/merchants/mer_1/reviews", headers=_auth(token))
        assert res.status_code == 200


class TestTransactionReads:
    def test_list_detail_and_audit_return_persisted_records(self, client: TestClient):
        _seed_transaction(client)
        token = _token(client, "user_admin")

        res = client.get("/merchants/mer_1/transactions", headers=_auth(token))
        assert res.status_code == 200, res.text
        assert [item["id"] for item in res.json()["items"]] == ["txn_1"]
        assert res.json()["items"][0]["state"] == "UNKNOWN"
        assert res.json()["items"][0]["amount"] == {
            "amount_minor": 120000,
            "currency": "INR",
        }

        res = client.get("/merchants/mer_1/transactions/txn_1", headers=_auth(token))
        assert res.status_code == 200, res.text
        assert res.json()["proposal_id"] == "prop_txn"
        assert res.json()["merchant_id"] == "mer_1"

        res = client.get("/merchants/mer_1/transactions/txn_1/audit", headers=_auth(token))
        assert res.status_code == 200, res.text
        assert res.json()["items"] == [
            {
                "id": "evt_1",
                "transaction_id": "txn_1",
                "event_type": "PROVIDER_OUTCOME_UNKNOWN",
                "actor_type": "SYSTEM",
                "actor_id": "payment-worker",
                "reason_code": "PROVIDER_TIMEOUT",
                "previous_state": "EXECUTING",
                "new_state": "UNKNOWN",
                "correlation_id": "corr_merchant_audit",
                "provider_reference_redacted": "order_***1234",
                "metadata": {"safe": "visible"},
                "created_at": res.json()["items"][0]["created_at"],
            }
        ]

    def test_unknown_transaction_is_not_found(self, client: TestClient):
        token = _token(client, "user_admin")
        res = client.get("/merchants/mer_1/transactions/missing", headers=_auth(token))
        assert res.status_code == 404

    def test_cross_tenant_list_is_denied(self, client: TestClient):
        token = _token(client, "user_admin")
        res = client.get("/merchants/mer_2/transactions", headers=_auth(token))
        assert res.status_code == 403

    def test_transactions_require_session(self, client: TestClient):
        res = client.get("/merchants/mer_1/transactions")
        assert res.status_code == 401
