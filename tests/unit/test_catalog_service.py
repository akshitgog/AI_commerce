from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.application.catalog_service import ApplicationMerchantCatalogService
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    CreateMerchantCommand,
    CreateProductCommand,
    Money,
    UpdateProductCommand,
)
from ai_commerce_gateway.core.errors import AppError
from ai_commerce_gateway.domain.enums import ActorType, MerchantRole, ProductStatus
from ai_commerce_gateway.infrastructure.database.merchant_repositories import (
    SqlAlchemyMerchantRepository,
    SqlAlchemyProductRepository,
)
from ai_commerce_gateway.infrastructure.database.models import Base


@pytest.fixture
def memory_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    session = session_factory()
    yield session
    session.close()
    engine.dispose()
    engine.dispose()


def _now() -> datetime:
    return datetime.now(tz=UTC)


def test_merchant_catalog_service_create_merchant(memory_session):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    service = ApplicationMerchantCatalogService(m_repo, p_repo)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id='cor1')
    cmd = CreateMerchantCommand(name="M1", idempotency_key="ik1")
    
    view = service.create_merchant(cmd, sys_actor)
    memory_session.commit()
    
    assert view.name == "M1"
    
    # Denial test
    bad_actor = ActorContext(actor_id="user1", actor_type=ActorType.MERCHANT_USER, correlation_id='cor1')  # noqa: E501
    with pytest.raises(AppError) as exc:
        service.create_merchant(cmd, bad_actor)
    assert exc.value.status_code == 403

def test_merchant_catalog_service_get_merchant(memory_session):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    service = ApplicationMerchantCatalogService(m_repo, p_repo)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id='cor1')
    cmd = CreateMerchantCommand(name="M1", idempotency_key="ik1")
    m_view = service.create_merchant(cmd, sys_actor)
    memory_session.commit()

    actor = ActorContext(
        actor_id="u1", 
        actor_type=ActorType.MERCHANT_USER, 
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.VIEWER]),
        correlation_id='cor1'
    )
    
    res = service.get_merchant(m_view.id, actor)
    assert res.id == m_view.id
    
    # Denial test
    actor_no_access = ActorContext(
        actor_id="u2", actor_type=ActorType.MERCHANT_USER, merchant_ids=frozenset(["other"]), correlation_id='cor1'  # noqa: E501
    )
    with pytest.raises(AppError) as exc:
        service.get_merchant(m_view.id, actor_no_access)
    assert exc.value.status_code == 403
    
    with pytest.raises(AppError) as exc:
        service.get_merchant("nonexistent", sys_actor)
    assert exc.value.status_code == 404

def test_merchant_catalog_service_create_product(memory_session):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    service = ApplicationMerchantCatalogService(m_repo, p_repo)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id='cor1')
    m_view = service.create_merchant(CreateMerchantCommand(name="M1", idempotency_key="ik1"), sys_actor)  # noqa: E501
    memory_session.commit()

    actor_admin = ActorContext(
        actor_id="u1", 
        actor_type=ActorType.MERCHANT_USER, 
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id='cor1'
    )
    
    cmd = CreateProductCommand(
        merchant_id=m_view.id,
        sku="SKU1",
        title="Prod1",
        description="Desc1",
        price=Money(amount_minor=1000, currency="USD"),
        available_quantity=5,
        idempotency_key="pk1"
    )
    
    p_view = service.create_product(cmd, actor_admin)
    memory_session.commit()
    
    assert p_view.sku == "SKU1"
    assert p_view.status == ProductStatus.DRAFT
    assert p_view.version == 1
    
    # Duplicate SKU test
    with pytest.raises(AppError) as exc:
        service.create_product(cmd, actor_admin)
    assert exc.value.status_code == 409
    
    # Denial test (insufficient role)
    actor_viewer = ActorContext(
        actor_id="u2", 
        actor_type=ActorType.MERCHANT_USER, 
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.VIEWER]),
        correlation_id='cor1'
    )
    with pytest.raises(AppError) as exc:
        service.create_product(cmd, actor_viewer)
    assert exc.value.status_code == 403

def test_merchant_catalog_service_update_product(memory_session):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    service = ApplicationMerchantCatalogService(m_repo, p_repo)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id='cor1')
    m_view = service.create_merchant(CreateMerchantCommand(name="M1", idempotency_key="ik1"), sys_actor)  # noqa: E501
    
    actor_admin = ActorContext(
        actor_id="u1", 
        actor_type=ActorType.MERCHANT_USER, 
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id='cor1'
    )
    
    cmd = CreateProductCommand(
        merchant_id=m_view.id, sku="SKU1", title="Prod1", description="Desc1",
        price=Money(amount_minor=1000, currency="USD"), available_quantity=5, idempotency_key="pk1"
    )
    p_view = service.create_product(cmd, actor_admin)
    memory_session.commit()
    
    up_cmd = UpdateProductCommand(
        merchant_id=m_view.id,
        product_id=p_view.id,
        expected_version=1,
        title="Prod1-New",
        idempotency_key="upk1"
    )
    
    up_view = service.update_product(up_cmd, actor_admin)
    memory_session.commit()
    
    assert up_view.title == "Prod1-New"
    assert up_view.version == 2
    
    # Stale write check
    with pytest.raises(AppError) as exc:
        service.update_product(up_cmd, actor_admin)
    assert exc.value.status_code == 409

    # Tenant denial check
    actor_admin_other = ActorContext(
        actor_id="u3", 
        actor_type=ActorType.MERCHANT_USER, 
        merchant_ids=frozenset(["other"]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id='cor1'
    )
    up_cmd_other = UpdateProductCommand(
        merchant_id="other", product_id=p_view.id, expected_version=2, idempotency_key="upk2"
    )
    with pytest.raises(AppError) as exc:
        service.update_product(up_cmd_other, actor_admin_other)
    assert exc.value.status_code == 404

def test_merchant_catalog_service_read_list_products(memory_session):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    service = ApplicationMerchantCatalogService(m_repo, p_repo)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id='cor1')
    m_view = service.create_merchant(CreateMerchantCommand(name="M1", idempotency_key="ik1"), sys_actor)  # noqa: E501
    
    actor_admin = ActorContext(
        actor_id="u1", 
        actor_type=ActorType.MERCHANT_USER, 
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id='cor1'
    )
    
    cmd1 = CreateProductCommand(
        merchant_id=m_view.id, sku="S1", title="P1", description="D1",
        price=Money(amount_minor=100, currency="USD"), available_quantity=1, idempotency_key="pk1"
    )
    cmd2 = CreateProductCommand(
        merchant_id=m_view.id, sku="S2", title="P2", description="D2",
        price=Money(amount_minor=200, currency="USD"), available_quantity=2, idempotency_key="pk2"
    )
    
    p1 = service.create_product(cmd1, actor_admin)
    p2 = service.create_product(cmd2, actor_admin)
    memory_session.commit()
    
    # Get product
    res_p1 = service.get_product(p1.id, actor_admin)
    assert res_p1.sku == "S1"
    
    # Denial get
    actor_other = ActorContext(actor_id="u2", actor_type=ActorType.MERCHANT_USER, merchant_ids=frozenset(["other"]), correlation_id='cor1')  # noqa: E501
    with pytest.raises(AppError) as exc:
        service.get_product(p1.id, actor_other)
    assert exc.value.status_code == 404
    
    # List products
    page = service.list_products(m_view.id, actor_admin)
    assert len(page.items) == 2
    assert page.items[0].id == p1.id
    assert page.items[1].id == p2.id
def test_merchant_catalog_service_list_products_pagination(memory_session):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    service = ApplicationMerchantCatalogService(m_repo, p_repo)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id='cor1')
    m_view = service.create_merchant(CreateMerchantCommand(name="M_Pag", idempotency_key="ik_pag"), sys_actor)  # noqa: E501
    
    actor_admin = ActorContext(
        actor_id="u1", 
        actor_type=ActorType.MERCHANT_USER, 
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id='cor1'
    )
    
    # Create 55 products
    for i in range(55):
        cmd = CreateProductCommand(
            merchant_id=m_view.id, sku=f"SKU_PAG_{i}", title=f"P_{i}", description="D",
            price=Money(amount_minor=100, currency="USD"), available_quantity=1, idempotency_key=f"pk_{i}"  # noqa: E501
        )
        service.create_product(cmd, actor_admin)
    
    memory_session.commit()
    
    # Page 1
    page1 = service.list_products(m_view.id, actor_admin)
    assert len(page1.items) == 50
    assert page1.next_cursor is not None
    
    # Page 2
    page2 = service.list_products(m_view.id, actor_admin, cursor=page1.next_cursor)
    assert len(page2.items) == 5
    assert page2.next_cursor is None

def test_merchant_catalog_service_system_get_product_not_implemented(memory_session):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    service = ApplicationMerchantCatalogService(m_repo, p_repo)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id='cor1')
    
    with pytest.raises(NotImplementedError) as exc:
        service.get_product("any_id", sys_actor)
    
    assert "System actor lookup without merchant_id not implemented" in str(exc.value)

def test_merchant_catalog_service_create_product_db_race(memory_session, monkeypatch):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    service = ApplicationMerchantCatalogService(m_repo, p_repo)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id='cor1')
    m_view = service.create_merchant(CreateMerchantCommand(name="M1", idempotency_key="ik1"), sys_actor)  # noqa: E501
    memory_session.commit()

    actor_admin = ActorContext(
        actor_id="u1", 
        actor_type=ActorType.MERCHANT_USER, 
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id='cor1'
    )
    
    cmd = CreateProductCommand(
        merchant_id=m_view.id,
        sku="SKU-RACE",
        title="Prod1",
        description="Desc1",
        price=Money(amount_minor=1000, currency="USD"),
        available_quantity=5,
        idempotency_key="pk1"
    )
    
    # First create succeeds
    service.create_product(cmd, actor_admin)
    memory_session.commit()
    
    # Mock the app-level check to simulate a concurrent race condition
    # where both transactions pass the application-level sku_exists_for_merchant check
    monkeypatch.setattr(p_repo, "sku_exists_for_merchant", lambda m_id, sku: False)
    
    # Second create should hit the DB unique constraint and raise AppError 409
    with pytest.raises(AppError) as exc:
        service.create_product(cmd, actor_admin)
    
    assert exc.value.status_code == 409
    assert "already exists" in str(exc.value)
def test_merchant_catalog_service_update_product_db_race(memory_session, monkeypatch):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    service = ApplicationMerchantCatalogService(m_repo, p_repo)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id='cor1')
    m_view = service.create_merchant(CreateMerchantCommand(name="M1", idempotency_key="ik1"), sys_actor)  # noqa: E501
    memory_session.commit()

    actor_admin = ActorContext(
        actor_id="u1", 
        actor_type=ActorType.MERCHANT_USER, 
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id='cor1'
    )
    
    cmd_create = CreateProductCommand(
        merchant_id=m_view.id,
        sku="SKU-UP-RACE",
        title="Prod1",
        description="Desc1",
        price=Money(amount_minor=1000, currency="USD"),
        available_quantity=5,
        idempotency_key="pk1"
    )
    p_view = service.create_product(cmd_create, actor_admin)
    memory_session.commit()
    
    cmd_update = UpdateProductCommand(
        merchant_id=m_view.id,
        product_id=p_view.id,
        expected_version=1,
        title="Updated Title",
        idempotency_key="pk2"
    )
    
    # First update succeeds, incrementing version to 2
    service.update_product(cmd_update, actor_admin)
    memory_session.commit()
    
    # Mock the app-level check to simulate a concurrent race condition
    # where both transactions passed the expected_version check in get_by_id
    # We patch get_by_id to return a mock product with version 1
    original_get = p_repo.get_by_id
    from dataclasses import replace
    def mock_get_by_id(merchant_id, product_id):
        prod = original_get(merchant_id, product_id)
        if prod:
            prod = replace(prod, version=1) # Fake the version so the app-level check passes
        return prod
    monkeypatch.setattr(p_repo, "get_by_id", mock_get_by_id)

    
    # Second update should hit the DB atomic constraint (rowcount == 0) and raise AppError 409
    with pytest.raises(AppError) as exc:
        service.update_product(cmd_update, actor_admin)
    
    assert exc.value.status_code == 409
    assert "stale write" in str(exc.value)

