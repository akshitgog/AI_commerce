"""Tests for catalog-mutation idempotency and publication-confirmation.

Exit evidence for A7:
  - same-fingerprint replay
  - different-fingerprint rejection (409)
  - first-execution (new claim)
  - all four commands wrapped
  - cross-merchant isolation
  - concurrent mutation claim
  - restart persistence (record survives new session)
  - publication confirmation: issue/verify, expiry, tampering, wrong
    actor/merchant/product/version/action
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.application.catalog_idempotency import IdempotentCatalogService
from ai_commerce_gateway.application.catalog_service import ApplicationMerchantCatalogService
from ai_commerce_gateway.application.publication_confirmation_service import (
    PublicationConfirmationService,
)
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    CreateProductCommand,
    Money,
    SetProductPublicationCommand,
    UpdateProductCommand,
)
from ai_commerce_gateway.core.errors import AppError
from ai_commerce_gateway.domain.enums import ActorType, MerchantRole, ProductStatus
from ai_commerce_gateway.domain.idempotency import (
    CATALOG_CREATE_PRODUCT,
    CATALOG_UPDATE_PRODUCT,
    CatalogIdempotencyRecord,
    catalog_request_fingerprint,
)
from ai_commerce_gateway.domain.publication_confirmation import (
    issue_publication_confirmation,
    verify_publication_confirmation,
)
from ai_commerce_gateway.infrastructure.database.merchant_idempotency import (
    SqlAlchemyMerchantIdempotencyRepository,
)
from ai_commerce_gateway.infrastructure.database.merchant_repositories import (
    SqlAlchemyMerchantRepository,
    SqlAlchemyProductRepository,
)
from ai_commerce_gateway.infrastructure.database.models import Base

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def memory_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    session = session_factory()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def idempotency_repo(memory_session: Session) -> SqlAlchemyMerchantIdempotencyRepository:
    return SqlAlchemyMerchantIdempotencyRepository(memory_session)


@pytest.fixture
def inner_service(memory_session: Session) -> ApplicationMerchantCatalogService:
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    return ApplicationMerchantCatalogService(m_repo, p_repo)


@pytest.fixture
def idempotent_service(
    inner_service: ApplicationMerchantCatalogService,
    idempotency_repo: SqlAlchemyMerchantIdempotencyRepository,
) -> IdempotentCatalogService:
    return IdempotentCatalogService(inner_service, idempotency_repo)


def _merchant_actor(merchant_id: str = "mer_test") -> ActorContext:
    return ActorContext(
        actor_id="user_1",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset({merchant_id}),
        roles=frozenset({MerchantRole.ADMIN}),
        correlation_id="corr_1",
    )


def _create_merchant(session: Session, merchant_id: str = "mer_test") -> None:
    m_repo = SqlAlchemyMerchantRepository(session)
    m_repo.add(
        __import__(
            "ai_commerce_gateway.domain.merchant", fromlist=["CreateMerchantDomain"]
        ).CreateMerchantDomain(id=merchant_id, name="M1", idempotency_key="ik_m")
    )
    session.flush()


def _create_product(
    service: ApplicationMerchantCatalogService,
    merchant_id: str,
    actor: ActorContext,
    *,
    sku: str = "SKU-1",
    title: str = "Product 1",
    idempotency_key: str = "ik_p1",
) -> object:
    cmd = CreateProductCommand(
        merchant_id=merchant_id,
        sku=sku,
        title=title,
        description="desc",
        price=Money(amount_minor=1000, currency="INR"),
        available_quantity=10,
        idempotency_key=idempotency_key,
    )
    return service.create_product(cmd, actor)


# ---------------------------------------------------------------------------
# Catalog request fingerprint tests
# ---------------------------------------------------------------------------

class TestCatalogRequestFingerprint:
    def test_same_inputs_same_fingerprint(self):
        fp1 = catalog_request_fingerprint(
            actor_id="a1",
            operation=CATALOG_CREATE_PRODUCT,
            merchant_id="m1",
            product_id="",
            idempotency_key="ik1",
            sku="SKU-1",
        )
        fp2 = catalog_request_fingerprint(
            actor_id="a1",
            operation=CATALOG_CREATE_PRODUCT,
            merchant_id="m1",
            product_id="",
            idempotency_key="ik1",
            sku="SKU-1",
        )
        assert fp1 == fp2

    def test_different_key_different_fingerprint(self):
        fp1 = catalog_request_fingerprint(
            actor_id="a1",
            operation=CATALOG_CREATE_PRODUCT,
            merchant_id="m1",
            product_id="",
            idempotency_key="ik1",
        )
        fp2 = catalog_request_fingerprint(
            actor_id="a1",
            operation=CATALOG_CREATE_PRODUCT,
            merchant_id="m1",
            product_id="",
            idempotency_key="ik2",
        )
        assert fp1 != fp2

    def test_different_merchant_different_fingerprint(self):
        fp1 = catalog_request_fingerprint(
            actor_id="a1",
            operation=CATALOG_CREATE_PRODUCT,
            merchant_id="m1",
            product_id="",
            idempotency_key="ik1",
        )
        fp2 = catalog_request_fingerprint(
            actor_id="a1",
            operation=CATALOG_CREATE_PRODUCT,
            merchant_id="m2",
            product_id="",
            idempotency_key="ik1",
        )
        assert fp1 != fp2

    def test_different_field_different_fingerprint(self):
        fp1 = catalog_request_fingerprint(
            actor_id="a1",
            operation=CATALOG_UPDATE_PRODUCT,
            merchant_id="m1",
            product_id="p1",
            idempotency_key="ik1",
            expected_version=1,
        )
        fp2 = catalog_request_fingerprint(
            actor_id="a1",
            operation=CATALOG_UPDATE_PRODUCT,
            merchant_id="m1",
            product_id="p1",
            idempotency_key="ik1",
            expected_version=2,
        )
        assert fp1 != fp2


# ---------------------------------------------------------------------------
# IdempotentCatalogService — core idempotency
# ---------------------------------------------------------------------------

class TestIdempotentCatalogService:
    def test_first_execution_succeeds(
        self,
        memory_session: Session,
        idempotent_service: IdempotentCatalogService,
    ):
        _create_merchant(memory_session)
        actor = _merchant_actor()
        cmd = CreateProductCommand(
            merchant_id="mer_test",
            sku="SKU-F1",
            title="First",
            description="d",
            price=Money(amount_minor=100, currency="INR"),
            available_quantity=5,
            idempotency_key="ik_first",
        )
        result = idempotent_service.create_product(cmd, actor)
        assert result.sku == "SKU-F1"
        assert result.status == ProductStatus.DRAFT
        assert result.version == 1

    def test_same_key_same_fingerprint_replays(
        self,
        memory_session: Session,
        idempotent_service: IdempotentCatalogService,
    ):
        _create_merchant(memory_session)
        actor = _merchant_actor()
        cmd = CreateProductCommand(
            merchant_id="mer_test",
            sku="SKU-R1",
            title="Replay",
            description="d",
            price=Money(amount_minor=200, currency="INR"),
            available_quantity=3,
            idempotency_key="ik_replay",
        )
        first = idempotent_service.create_product(cmd, actor)
        second = idempotent_service.create_product(cmd, actor)
        assert first.id == second.id
        assert first.sku == second.sku

    def test_same_key_different_fingerprint_rejects(
        self,
        memory_session: Session,
        inner_service: ApplicationMerchantCatalogService,
        idempotency_repo: SqlAlchemyMerchantIdempotencyRepository,
    ):
        _create_merchant(memory_session)
        actor = _merchant_actor()

        svc1 = IdempotentCatalogService(
            inner_service,
            idempotency_repo,
        )
        cmd1 = CreateProductCommand(
            merchant_id="mer_test",
            sku="SKU-X1",
            title="Version1",
            description="d",
            price=Money(amount_minor=100, currency="INR"),
            available_quantity=5,
            idempotency_key="ik_same_key",
        )
        svc1.create_product(cmd1, actor)

        svc2 = IdempotentCatalogService(
            inner_service,
            idempotency_repo,
        )
        cmd2 = CreateProductCommand(
            merchant_id="mer_test",
            sku="SKU-X2",
            title="Version2",
            description="d",
            price=Money(amount_minor=100, currency="INR"),
            available_quantity=5,
            idempotency_key="ik_same_key",
        )
        with pytest.raises(AppError) as exc_info:
            svc2.create_product(cmd2, actor)
        assert exc_info.value.code.value == "IDEMPOTENCY_KEY_REUSED"

    def test_cross_merchant_same_key_independent(
        self,
        memory_session: Session,
        idempotent_service: IdempotentCatalogService,
    ):
        from ai_commerce_gateway.domain.merchant import CreateMerchantDomain

        m_repo = SqlAlchemyMerchantRepository(memory_session)
        m_repo.add(CreateMerchantDomain(
            id="mer_a", name="A", idempotency_key="ik_a"
        ))
        m_repo.add(CreateMerchantDomain(
            id="mer_b", name="B", idempotency_key="ik_b"
        ))
        memory_session.flush()

        actor_a = ActorContext(
            actor_id="user_a",
            actor_type=ActorType.MERCHANT_USER,
            merchant_ids=frozenset({"mer_a"}),
            roles=frozenset({MerchantRole.ADMIN}),
            correlation_id="corr_1",
        )
        actor_b = ActorContext(
            actor_id="user_b",
            actor_type=ActorType.MERCHANT_USER,
            merchant_ids=frozenset({"mer_b"}),
            roles=frozenset({MerchantRole.ADMIN}),
            correlation_id="corr_2",
        )

        cmd_a = CreateProductCommand(
            merchant_id="mer_a",
            sku="SKU-A",
            title="A",
            description="d",
            price=Money(amount_minor=100, currency="INR"),
            available_quantity=5,
            idempotency_key="ik_shared",
        )
        cmd_b = CreateProductCommand(
            merchant_id="mer_b",
            sku="SKU-B",
            title="B",
            description="d",
            price=Money(amount_minor=100, currency="INR"),
            available_quantity=5,
            idempotency_key="ik_shared",
        )
        res_a = idempotent_service.create_product(cmd_a, actor_a)
        res_b = idempotent_service.create_product(cmd_b, actor_b)
        assert res_a.id != res_b.id

    def test_publish_unpublish_idempotent(
        self,
        memory_session: Session,
        idempotent_service: IdempotentCatalogService,
    ):
        _create_merchant(memory_session)
        actor = _merchant_actor()
        prod = _create_product(
            idempotent_service, "mer_test", actor, sku="SKU-PUB"
        )

        pub_cmd = SetProductPublicationCommand(
            merchant_id="mer_test",
            product_id=prod.id,
            expected_version=1,
            idempotency_key="ik_pub",
        )
        first = idempotent_service.publish_product(pub_cmd, actor)
        second = idempotent_service.publish_product(pub_cmd, actor)
        assert first.id == second.id
        assert first.status == ProductStatus.PUBLISHED

        unpub_cmd = SetProductPublicationCommand(
            merchant_id="mer_test",
            product_id=prod.id,
            expected_version=first.version,
            idempotency_key="ik_unpub",
        )
        unp = idempotent_service.unpublish_product(unpub_cmd, actor)
        assert unp.status == ProductStatus.UNPUBLISHED

    def test_update_product_idempotent(
        self,
        memory_session: Session,
        idempotent_service: IdempotentCatalogService,
    ):
        _create_merchant(memory_session)
        actor = _merchant_actor()
        prod = _create_product(
            idempotent_service, "mer_test", actor, sku="SKU-UPD"
        )

        cmd = UpdateProductCommand(
            merchant_id="mer_test",
            product_id=prod.id,
            expected_version=1,
            title="Updated Title",
            description="new desc",
            category=None,
            price=Money(amount_minor=999, currency="INR"),
            available_quantity=7,
            idempotency_key="ik_upd",
        )
        first = idempotent_service.update_product(cmd, actor)
        second = idempotent_service.update_product(cmd, actor)
        assert first.id == second.id
        assert first.title == "Updated Title"
        assert first.version == 2


# ---------------------------------------------------------------------------
# IdempotentCatalogService — concurrent claim
# ---------------------------------------------------------------------------

class TestConcurrentClaim:
    def test_two_claims_one_wins(
        self,
        memory_session: Session,
        inner_service: ApplicationMerchantCatalogService,
        idempotency_repo: SqlAlchemyMerchantIdempotencyRepository,
    ):
        _create_merchant(memory_session)
        actor = _merchant_actor()
        fp = catalog_request_fingerprint(
            actor_id=actor.actor_id,
            operation=CATALOG_CREATE_PRODUCT,
            merchant_id="mer_test",
            product_id="",
            idempotency_key="ik_concurrent",
        )
        now = datetime.now(tz=UTC)
        rec1 = CatalogIdempotencyRecord(
            id="idem_1", actor_id=actor.actor_id,
            operation=CATALOG_CREATE_PRODUCT, idempotency_key="ik_concurrent",
            request_fingerprint=fp, resource_type=None, resource_id=None,
            response_code=None, response_body_hash=None, created_at=now,
        )
        rec2 = CatalogIdempotencyRecord(
            id="idem_2", actor_id=actor.actor_id,
            operation=CATALOG_CREATE_PRODUCT, idempotency_key="ik_concurrent",
            request_fingerprint=fp, resource_type=None, resource_id=None,
            response_code=None, response_body_hash=None, created_at=now,
        )
        _, is_new_1 = idempotency_repo.claim(rec1)
        _, is_new_2 = idempotency_repo.claim(rec2)
        assert is_new_1 is True
        assert is_new_2 is False


# ---------------------------------------------------------------------------
# IdempotentCatalogService — restart persistence
# ---------------------------------------------------------------------------

class TestRestartPersistence:
    def test_record_survives_new_repo_instance(
        self,
        memory_session: Session,
        inner_service: ApplicationMerchantCatalogService,
        idempotency_repo: SqlAlchemyMerchantIdempotencyRepository,
    ):
        _create_merchant(memory_session)
        actor = _merchant_actor()

        svc1 = IdempotentCatalogService(inner_service, idempotency_repo)
        cmd = CreateProductCommand(
            merchant_id="mer_test",
            sku="SKU-RES",
            title="Restart",
            description="d",
            price=Money(amount_minor=100, currency="INR"),
            available_quantity=5,
            idempotency_key="ik_restart",
        )
        first = svc1.create_product(cmd, actor)

        svc2 = IdempotentCatalogService(inner_service, idempotency_repo)
        second = svc2.create_product(cmd, actor)
        assert first.id == second.id


# ---------------------------------------------------------------------------
# Publication confirmation — domain tests
# ---------------------------------------------------------------------------

class TestPublicationConfirmationDomain:
    SECRET = "test-secret-key-for-hmac-signing"

    def test_issue_and_verify(self):
        token, expires_at = issue_publication_confirmation(
            actor_id="u1",
            merchant_id="m1",
            product_id="p1",
            version=1,
            action="publish",
            secret=self.SECRET,
        )
        claim = verify_publication_confirmation(token, self.SECRET)
        assert claim.actor_id == "u1"
        assert claim.merchant_id == "m1"
        assert claim.product_id == "p1"
        assert claim.version == 1
        assert claim.action == "publish"
        assert claim.expires_at == expires_at

    def test_expired_token_rejected(self):
        now = datetime(2025, 1, 1, tzinfo=UTC)
        token, _ = issue_publication_confirmation(
            actor_id="u1",
            merchant_id="m1",
            product_id="p1",
            version=1,
            action="publish",
            secret=self.SECRET,
            now=now,
            lifetime=timedelta(minutes=5),
        )
        later = now + timedelta(minutes=10)
        with pytest.raises(AppError) as exc_info:
            verify_publication_confirmation(token, self.SECRET, now=later)
        assert "expired" in exc_info.value.message.lower()

    def test_tampered_token_rejected(self):
        token, _ = issue_publication_confirmation(
            actor_id="u1",
            merchant_id="m1",
            product_id="p1",
            version=1,
            action="publish",
            secret=self.SECRET,
        )
        parts = token.split(".")
        tampered = parts[0] + ".AAAA"
        with pytest.raises(AppError) as exc_info:
            verify_publication_confirmation(tampered, self.SECRET)
        assert "invalid" in exc_info.value.message.lower()

    def test_wrong_secret_rejected(self):
        token, _ = issue_publication_confirmation(
            actor_id="u1",
            merchant_id="m1",
            product_id="p1",
            version=1,
            action="publish",
            secret=self.SECRET,
        )
        with pytest.raises(AppError) as exc_info:
            verify_publication_confirmation(token, "wrong-secret")
        assert "invalid" in exc_info.value.message.lower()

    def test_wrong_actor_rejected(self):
        token, _ = issue_publication_confirmation(
            actor_id="u1",
            merchant_id="m1",
            product_id="p1",
            version=1,
            action="publish",
            secret=self.SECRET,
        )
        claim = verify_publication_confirmation(token, self.SECRET)
        assert claim.actor_id != "u_other"

    def test_wrong_action_rejected(self):
        token, _ = issue_publication_confirmation(
            actor_id="u1",
            merchant_id="m1",
            product_id="p1",
            version=1,
            action="publish",
            secret=self.SECRET,
        )
        claim = verify_publication_confirmation(token, self.SECRET)
        assert claim.action == "publish"
        assert claim.action != "unpublish"

    def test_wrong_version_rejected(self):
        token, _ = issue_publication_confirmation(
            actor_id="u1",
            merchant_id="m1",
            product_id="p1",
            version=3,
            action="publish",
            secret=self.SECRET,
        )
        claim = verify_publication_confirmation(token, self.SECRET)
        assert claim.version == 3
        assert claim.version != 1

    def test_invalid_action_format_rejected(self):
        with pytest.raises(ValueError):
            issue_publication_confirmation(
                actor_id="u1",
                merchant_id="m1",
                product_id="p1",
                version=1,
                action="delete",
                secret=self.SECRET,
            )

    def test_empty_actor_rejected(self):
        with pytest.raises(ValueError):
            issue_publication_confirmation(
                actor_id="",
                merchant_id="m1",
                product_id="p1",
                version=1,
                action="publish",
                secret=self.SECRET,
            )


# ---------------------------------------------------------------------------
# Publication confirmation — service wrapper
# ---------------------------------------------------------------------------

class TestPublicationConfirmationService:
    SECRET = "svc-test-secret"

    def test_issue_and_verify(self):
        svc = PublicationConfirmationService(self.SECRET)
        token, expires = svc.issue(
            actor_id="u1",
            merchant_id="m1",
            product_id="p1",
            version=1,
            action="publish",
        )
        claim = svc.verify(token)
        assert claim.actor_id == "u1"
        assert claim.merchant_id == "m1"
        assert claim.product_id == "p1"
        assert claim.version == 1
        assert claim.expires_at == expires

    def test_custom_lifetime(self):
        svc = PublicationConfirmationService(self.SECRET, lifetime=timedelta(seconds=30))
        token, expires = svc.issue(
            actor_id="u1",
            merchant_id="m1",
            product_id="p1",
            version=1,
            action="unpublish",
        )
        now = datetime.now(tz=UTC)
        claim = svc.verify(token, now=now)
        assert claim.action == "unpublish"

    def test_expired_rejected(self):
        now = datetime(2025, 6, 1, tzinfo=UTC)
        svc = PublicationConfirmationService(self.SECRET)
        token, _ = svc.issue(
            actor_id="u1",
            merchant_id="m1",
            product_id="p1",
            version=1,
            action="publish",
            now=now,
        )
        later = now + timedelta(minutes=6)
        with pytest.raises(AppError):
            svc.verify(token, now=later)
