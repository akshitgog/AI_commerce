"""P0-2 merchant session boundary unit tests.

Identity, roles and tenant scope come only from server-side state
(membership repository + server-minted opaque tokens) — never from
client-supplied headers or bodies.
"""

from datetime import timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.application.merchant_sessions import (
    InMemoryMerchantSessionService,
    MerchantAuthenticationError,
)
from ai_commerce_gateway.domain.enums import MerchantRole
from ai_commerce_gateway.domain.merchant import (
    AddMerchantUserDomain,
    CreateMerchantDomain,
)
from ai_commerce_gateway.infrastructure.database.merchant_repositories import (
    SqlAlchemyMerchantRepository,
    SqlAlchemyMerchantUserRepository,
)
from ai_commerce_gateway.infrastructure.database.models import Base


@pytest.fixture
def session_db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    session = factory()
    yield session
    session.close()
    engine.dispose()


def _seed_member(db: Session, role: MerchantRole = MerchantRole.ADMIN) -> None:
    m_repo = SqlAlchemyMerchantRepository(db)
    u_repo = SqlAlchemyMerchantUserRepository(db)
    m_repo.add(CreateMerchantDomain(id="mer_1", name="M", idempotency_key="ik_m"))
    u_repo.add(
        AddMerchantUserDomain(id="mu_1", merchant_id="mer_1", user_id="user_1", role=role)
    )
    db.flush()


def test_issue_resolves_roles_from_database(session_db: Session):
    _seed_member(session_db, role=MerchantRole.VIEWER)
    svc = InMemoryMerchantSessionService(SqlAlchemyMerchantUserRepository(session_db))
    session = svc.issue("mer_1", "user_1")
    assert session.role is MerchantRole.VIEWER  # from DB, not from caller
    assert session.token.startswith("msess_")


def test_issue_rejects_unknown_membership(session_db: Session):
    _seed_member(session_db)
    svc = InMemoryMerchantSessionService(SqlAlchemyMerchantUserRepository(session_db))
    with pytest.raises(MerchantAuthenticationError):
        svc.issue("mer_1", "user_404")
    with pytest.raises(MerchantAuthenticationError):
        svc.issue("mer_404", "user_1")


def test_resolve_roundtrip_and_revoke(session_db: Session):
    _seed_member(session_db)
    svc = InMemoryMerchantSessionService(SqlAlchemyMerchantUserRepository(session_db))
    session = svc.issue("mer_1", "user_1")
    resolved = svc.resolve(session.token)
    assert resolved is not None and resolved.user_id == "user_1"
    svc.revoke(session.token)
    assert svc.resolve(session.token) is None


def test_resolve_rejects_forged_token(session_db: Session):
    _seed_member(session_db)
    svc = InMemoryMerchantSessionService(SqlAlchemyMerchantUserRepository(session_db))
    assert svc.resolve("msess_forged") is None


def test_expired_session_resolves_to_none(session_db: Session):
    _seed_member(session_db)
    svc = InMemoryMerchantSessionService(
        SqlAlchemyMerchantUserRepository(session_db), ttl=timedelta(seconds=0)
    )
    session = svc.issue("mer_1", "user_1")
    assert svc.resolve(session.token) is None


def test_demotion_takes_effect_mid_session(session_db: Session):
    _seed_member(session_db, role=MerchantRole.ADMIN)
    u_repo = SqlAlchemyMerchantUserRepository(session_db)
    svc = InMemoryMerchantSessionService(u_repo)
    session = svc.issue("mer_1", "user_1")
    assert svc.resolve(session.token).role is MerchantRole.ADMIN

    # Demote in the database; the next resolve must reflect it.
    from ai_commerce_gateway.infrastructure.database.models import MerchantUser

    record = session_db.query(MerchantUser).one()
    record.role = MerchantRole.VIEWER.value
    session_db.flush()
    assert svc.resolve(session.token).role is MerchantRole.VIEWER


def test_shared_store_survives_service_instances(session_db: Session):
    _seed_member(session_db)
    store: dict = {}
    svc_a = InMemoryMerchantSessionService(
        SqlAlchemyMerchantUserRepository(session_db), store=store
    )
    session = svc_a.issue("mer_1", "user_1")
    svc_b = InMemoryMerchantSessionService(
        SqlAlchemyMerchantUserRepository(session_db), store=store
    )
    assert svc_b.resolve(session.token) is not None
