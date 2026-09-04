"""D-010 extraction endpoint tests over the session boundary (P0-2/P0-6).

Identity comes only from a server-side session token; role checks are
server-side; the endpoint remains propose-only.
"""

from collections.abc import Iterator

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
    app.dependency_overrides[get_db_session] = override_db

    seed = factory()
    SqlAlchemyMerchantRepository(seed).add(
        CreateMerchantDomain(id="mer_1", name="Demo Merchant", idempotency_key="ik_seed_m")
    )
    SqlAlchemyMerchantRepository(seed).add(
        CreateMerchantDomain(id="mer_2", name="Other Merchant", idempotency_key="ik_seed_m2")
    )
    user_repo = SqlAlchemyMerchantUserRepository(seed)
    user_repo.add(
        AddMerchantUserDomain(
            id="mu_admin", merchant_id="mer_1", user_id="user_admin", role=MerchantRole.ADMIN
        )
    )
    user_repo.add(
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


URL = "/merchants/mer_1/products/extract-draft"


class TestExtractDraftEndpoint:
    def test_happy_path(self, client: TestClient):
        token = _token(client, "user_admin")
        res = client.post(
            URL,
            json={"text": "65W GaN Fast Charger. Price is ₹1,699 and I have 25 units."},
            headers=_auth(token),
        )
        assert res.status_code == 200
        body = res.json()
        assert body["persisted"] is False
        draft = body["draft"]
        assert draft["title"] == "65W GaN Fast Charger"
        assert draft["price_amount_minor"] == 169900
        assert draft["available_quantity"] == 25
        assert draft["source"] == "stub"

    def test_no_token_401(self, client: TestClient):
        res = client.post(URL, json={"text": "A wooden stool"})
        assert res.status_code == 401

    def test_forged_token_401(self, client: TestClient):
        res = client.post(
            URL,
            json={"text": "A wooden stool"},
            headers=_auth("msess_forged"),
        )
        assert res.status_code == 401

    def test_viewer_role_403(self, client: TestClient):
        token = _token(client, "user_viewer")
        res = client.post(URL, json={"text": "A wooden stool"}, headers=_auth(token))
        assert res.status_code == 403

    def test_wrong_tenant_403(self, client: TestClient):
        token = _token(client, "user_admin", merchant_id="mer_1")
        res = client.post(
            "/merchants/mer_2/products/extract-draft",
            json={"text": "A wooden stool"},
            headers=_auth(token),
        )
        assert res.status_code == 403

    def test_empty_text_400(self, client: TestClient):
        token = _token(client, "user_admin")
        res = client.post(URL, json={"text": "   "}, headers=_auth(token))
        assert res.status_code == 400

    def test_oversized_text_422(self, client: TestClient):
        token = _token(client, "user_admin")
        res = client.post(URL, json={"text": "x" * 4001}, headers=_auth(token))
        assert res.status_code == 422

    def test_unknown_user_cannot_get_session(self, client: TestClient):
        res = client.post("/merchants/mer_1/sessions", json={"user_id": "ghost"})
        assert res.status_code == 401
