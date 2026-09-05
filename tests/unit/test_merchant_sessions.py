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
    u_repo.add(AddMerchantUserDomain(id="mu_1", merchant_id="mer_1", user_id="user_1", role=role))
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


class TestDurableSessions:
    """SqlAlchemy store: sessions survive a simulated restart (fresh engine)."""

    def test_session_survives_restart(self, tmp_path):
        from ai_commerce_gateway.infrastructure.database.merchant_sessions import (
            SqlAlchemyMerchantSessionService,
        )

        url = f"sqlite:///{(tmp_path / 'sessions.db').as_posix()}"

        engine1 = create_engine(url)
        Base.metadata.create_all(engine1)
        s1 = sessionmaker(bind=engine1, autoflush=False)()
        SqlAlchemyMerchantRepository(s1).add(
            CreateMerchantDomain(id="mer_1", name="M", idempotency_key="ik_m")
        )
        SqlAlchemyMerchantUserRepository(s1).add(
            AddMerchantUserDomain(
                id="mu_1", merchant_id="mer_1", user_id="user_1", role=MerchantRole.EDITOR
            )
        )
        s1.commit()
        svc1 = SqlAlchemyMerchantSessionService(SqlAlchemyMerchantUserRepository(s1), s1)
        raw_token = svc1.issue("mer_1", "user_1").token
        s1.commit()
        s1.close()
        engine1.dispose()

        # Simulated restart: brand-new engine, session and service instance.
        engine2 = create_engine(url)
        s2 = sessionmaker(bind=engine2, autoflush=False)()
        svc2 = SqlAlchemyMerchantSessionService(SqlAlchemyMerchantUserRepository(s2), s2)
        resolved = svc2.resolve(raw_token)
        assert resolved is not None
        assert resolved.user_id == "user_1"
        assert resolved.role is MerchantRole.EDITOR

        # Revocation also persists across a further restart.
        svc2.revoke(raw_token)
        s2.commit()
        s2.close()
        engine2.dispose()
        engine3 = create_engine(url)
        s3 = sessionmaker(bind=engine3, autoflush=False)()
        svc3 = SqlAlchemyMerchantSessionService(SqlAlchemyMerchantUserRepository(s3), s3)
        assert svc3.resolve(raw_token) is None
        s3.close()
        engine3.dispose()

    def test_raw_token_never_persisted(self, tmp_path):
        from ai_commerce_gateway.infrastructure.database.merchant_sessions import (
            SqlAlchemyMerchantSessionService,
        )
        from ai_commerce_gateway.infrastructure.database.models import MerchantSessionRecord

        url = f"sqlite:///{(tmp_path / 'sessions2.db').as_posix()}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        s = sessionmaker(bind=engine, autoflush=False)()
        SqlAlchemyMerchantRepository(s).add(
            CreateMerchantDomain(id="mer_1", name="M", idempotency_key="ik_m")
        )
        SqlAlchemyMerchantUserRepository(s).add(
            AddMerchantUserDomain(
                id="mu_1", merchant_id="mer_1", user_id="user_1", role=MerchantRole.ADMIN
            )
        )
        s.commit()
        svc = SqlAlchemyMerchantSessionService(SqlAlchemyMerchantUserRepository(s), s)
        issued = svc.issue("mer_1", "user_1")
        s.commit()
        row = s.query(MerchantSessionRecord).one()
        assert row.token_hash != issued.token
        assert issued.token not in str(row.token_hash)
        assert len(row.token_hash) == 64  # sha256 hex
        s.close()
        engine.dispose()


class TestSessionAuditEvents:
    """P0-7 auth-boundary auditing: issue/failure/revoke are logged, secret-free."""

    def _records(self, caplog) -> list[dict]:
        import json

        return [
            json.loads(rec.message)
            for rec in caplog.records
            if rec.name == "ai_commerce_gateway.catalog_audit"
        ]

    def test_issue_emits_event(self, session_db: Session, caplog):
        import logging

        _seed_member(session_db)
        svc = InMemoryMerchantSessionService(SqlAlchemyMerchantUserRepository(session_db))
        with caplog.at_level(logging.INFO, logger="ai_commerce_gateway.catalog_audit"):
            session = svc.issue("mer_1", "user_1", correlation_id="corr_sess_1")

        events = self._records(caplog)
        assert len(events) == 1
        evt = events[0]
        assert evt["action"] == "session.issue"
        assert evt["actor_id"] == "user_1"
        assert evt["merchant_id"] == "mer_1"
        assert evt["target_type"] == "session"
        assert evt["correlation_id"] == "corr_sess_1"
        # Never log token material — not even the hash.
        assert session.token not in str(caplog.records)
        assert "msess_" not in str(caplog.records)

    def test_failed_issue_emits_event(self, session_db: Session, caplog):
        import logging

        _seed_member(session_db)
        svc = InMemoryMerchantSessionService(SqlAlchemyMerchantUserRepository(session_db))
        with caplog.at_level(logging.INFO, logger="ai_commerce_gateway.catalog_audit"):
            with pytest.raises(MerchantAuthenticationError):
                svc.issue("mer_1", "ghost", correlation_id="corr_fail")

        events = self._records(caplog)
        assert len(events) == 1
        assert events[0]["action"] == "session.issue_failed"
        assert events[0]["actor_id"] == "ghost"

    def test_revoke_emits_event(self, session_db: Session, caplog):
        import logging

        _seed_member(session_db)
        svc = InMemoryMerchantSessionService(SqlAlchemyMerchantUserRepository(session_db))
        session = svc.issue("mer_1", "user_1")
        with caplog.at_level(logging.INFO, logger="ai_commerce_gateway.catalog_audit"):
            caplog.clear()
            svc.revoke(session.token, correlation_id="corr_rev")

        events = self._records(caplog)
        assert len(events) == 1
        assert events[0]["action"] == "session.revoke"
        assert events[0]["correlation_id"] == "corr_rev"

    def test_revoke_unknown_token_emits_nothing(self, session_db: Session, caplog):
        import logging

        _seed_member(session_db)
        svc = InMemoryMerchantSessionService(SqlAlchemyMerchantUserRepository(session_db))
        with caplog.at_level(logging.INFO, logger="ai_commerce_gateway.catalog_audit"):
            svc.revoke("msess_nonexistent")
        assert self._records(caplog) == []
