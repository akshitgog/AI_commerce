"""P0-7 structured catalog audit event tests.

Events carry actor, action, tenant, target, correlation, causation and
before/after version/state — and provably never carry secrets, API keys,
confirmation tokens or sensitive payloads.
"""

import json
import logging

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.application.catalog_service import ApplicationMerchantCatalogService
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    CreateProductCommand,
    Money,
    UpdateProductCommand,
)
from ai_commerce_gateway.domain.enums import ActorType, MerchantRole
from ai_commerce_gateway.domain.merchant import CreateMerchantDomain
from ai_commerce_gateway.infrastructure.database.merchant_repositories import (
    SqlAlchemyMerchantRepository,
    SqlAlchemyProductRepository,
)
from ai_commerce_gateway.infrastructure.database.models import Base


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    session = factory()
    yield session
    session.close()
    engine.dispose()


def _actor() -> ActorContext:
    return ActorContext(
        actor_id="user_1",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset({"mer_1"}),
        roles=frozenset({MerchantRole.ADMIN}),
        correlation_id="corr_audit_1",
    )


def _service(db: Session) -> ApplicationMerchantCatalogService:
    return ApplicationMerchantCatalogService(
        SqlAlchemyMerchantRepository(db), SqlAlchemyProductRepository(db)
    )


def _seed(db: Session) -> None:
    SqlAlchemyMerchantRepository(db).add(
        CreateMerchantDomain(id="mer_1", name="M", idempotency_key="ik_m")
    )
    db.flush()


def _records(caplog) -> list[dict]:
    return [
        json.loads(rec.message)
        for rec in caplog.records
        if rec.name == "ai_commerce_gateway.catalog_audit"
    ]


def test_create_emits_structured_event(db: Session, caplog: pytest.LogCaptureFixture):
    _seed(db)
    actor = _actor()
    with caplog.at_level(logging.INFO, logger="ai_commerce_gateway.catalog_audit"):
        _service(db).create_product(
            CreateProductCommand(
                merchant_id="mer_1",
                sku="SKU-1",
                title="Charger",
                description="d",
                price=Money(amount_minor=169900, currency="INR"),
                available_quantity=25,
                idempotency_key="ik_create",
            ),
            actor,
        )

    events = _records(caplog)
    assert len(events) == 1
    evt = events[0]
    assert evt["actor_id"] == "user_1"
    assert evt["actor_type"] == "MERCHANT_USER"
    assert evt["action"] == "product.create"
    assert evt["merchant_id"] == "mer_1"
    assert evt["target_type"] == "product"
    assert evt["target_id"].startswith("prod_")
    assert evt["correlation_id"] == "corr_audit_1"
    assert evt["causation"] == "ik_create"
    assert evt["before"] is None
    assert evt["after"]["price_minor"] == 169900
    assert evt["version_after"] == 1
    assert evt["occurred_at"]


def test_update_emits_before_after_versions(db: Session, caplog: pytest.LogCaptureFixture):
    _seed(db)
    actor = _actor()
    service = _service(db)
    product = service.create_product(
        CreateProductCommand(
            merchant_id="mer_1",
            sku="SKU-2",
            title="Charger",
            description="d",
            price=Money(amount_minor=100, currency="INR"),
            available_quantity=1,
            idempotency_key="ik_c2",
        ),
        actor,
    )

    with caplog.at_level(logging.INFO, logger="ai_commerce_gateway.catalog_audit"):
        caplog.clear()
        service.update_product(
            UpdateProductCommand(
                merchant_id="mer_1",
                product_id=product.id,
                expected_version=1,
                title="Charger Pro",
                idempotency_key="ik_update",
            ),
            actor,
        )

    events = _records(caplog)
    assert len(events) == 1
    evt = events[0]
    assert evt["action"] == "product.update"
    assert evt["version_before"] == 1
    assert evt["version_after"] == 2
    assert evt["before"]["price_minor"] == 100
    assert evt["after"]["status"] == "DRAFT"


def test_events_contain_no_secrets(db: Session, caplog: pytest.LogCaptureFixture):
    """Secrets, tokens and API keys can never appear in audit output."""
    _seed(db)
    actor = _actor()
    with caplog.at_level(logging.INFO, logger="ai_commerce_gateway.catalog_audit"):
        _service(db).create_product(
            CreateProductCommand(
                merchant_id="mer_1",
                sku="SKU-3",
                title="Charger",
                description="d",
                price=Money(amount_minor=100, currency="INR"),
                available_quantity=1,
                idempotency_key="ik_no_leak",
            ),
            actor,
        )

    raw = "\n".join(rec.message for rec in caplog.records)
    for forbidden in ("confirmation_token", "msess_", "sk-", "pc_", "api_key", "secret"):
        assert forbidden not in raw


def test_audit_disabled_when_emitter_none(db: Session, caplog: pytest.LogCaptureFixture):
    _seed(db)
    service = ApplicationMerchantCatalogService(
        SqlAlchemyMerchantRepository(db),
        SqlAlchemyProductRepository(db),
        audit_emitter=None,
    )
    with caplog.at_level(logging.INFO, logger="ai_commerce_gateway.catalog_audit"):
        service.create_product(
            CreateProductCommand(
                merchant_id="mer_1",
                sku="SKU-4",
                title="Quiet",
                description="d",
                price=Money(amount_minor=100, currency="INR"),
                available_quantity=1,
                idempotency_key="ik_quiet",
            ),
            _actor(),
        )
    assert _records(caplog) == []
