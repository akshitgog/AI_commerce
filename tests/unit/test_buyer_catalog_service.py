import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ai_commerce_gateway.application.buyer_catalog_service import ApplicationCatalogService
from ai_commerce_gateway.application.catalog_service import ApplicationMerchantCatalogService
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    CatalogSearchQuery,
    CreateMerchantCommand,
    CreateProductCommand,
    Money,
    SetProductPublicationCommand,
)
from ai_commerce_gateway.core.errors import AppError
from ai_commerce_gateway.domain.enums import ActorType, MerchantRole
from ai_commerce_gateway.infrastructure.database.merchant_repositories import (
    SqlAlchemyMerchantRepository,
    SqlAlchemyProductRepository,
)
from ai_commerce_gateway.infrastructure.database.models import Base


@pytest.fixture
def memory_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    engine.dispose()


def test_buyer_catalog_service(memory_session):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    merchant_svc = ApplicationMerchantCatalogService(m_repo, p_repo)
    buyer_svc = ApplicationCatalogService(p_repo)

    sys_actor = ActorContext(actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id='cor1')
    m_view = merchant_svc.create_merchant(CreateMerchantCommand(name="M_Buyer", idempotency_key="ik"), sys_actor)  # noqa: E501
    memory_session.commit()

    actor_admin = ActorContext(
        actor_id="u1", actor_type=ActorType.MERCHANT_USER, 
        merchant_ids=frozenset([m_view.id]), roles=frozenset([MerchantRole.ADMIN]), correlation_id='cor1'  # noqa: E501
    )
    buyer_actor = ActorContext(actor_id="buyer1", actor_type=ActorType.BUYER, correlation_id='cor2')  # noqa: E501

    # Create two products, one published and one draft
    p1 = merchant_svc.create_product(CreateProductCommand(
        merchant_id=m_view.id, sku="SKU1", title="Published Prod", description="A great item",
        price=Money(amount_minor=500, currency="USD"), available_quantity=10, idempotency_key="pk1"
    ), actor_admin)
    memory_session.commit()
    
    # Publish p1
    merchant_svc.publish_product(SetProductPublicationCommand(
        merchant_id=m_view.id, product_id=p1.id, expected_version=1, idempotency_key="pk_pub"
    ), actor_admin)
    memory_session.commit()

    p2 = merchant_svc.create_product(CreateProductCommand(
        merchant_id=m_view.id, sku="SKU2", title="Draft Prod", description="Secret item",
        price=Money(amount_minor=1000, currency="USD"), available_quantity=5, idempotency_key="pk2"
    ), actor_admin)
    memory_session.commit()
    
    # Test draft invisibility
    with pytest.raises(AppError) as exc:
        buyer_svc.get_product(m_view.id, p2.id, buyer_actor)
    assert exc.value.status_code == 404
    
    # Test published visibility
    res = buyer_svc.get_product(m_view.id, p1.id, buyer_actor)
    assert res.id == p1.id
    
    # Test search filters (should only return published p1)
    q1 = CatalogSearchQuery(merchant_id=m_view.id)
    search_res = buyer_svc.search(q1, buyer_actor)
    assert len(search_res.items) == 1
    assert search_res.items[0].id == p1.id
    
    # Test search filter by query string
    q2 = CatalogSearchQuery(merchant_id=m_view.id, query="great")
    assert len(buyer_svc.search(q2, buyer_actor).items) == 1
    
    q3 = CatalogSearchQuery(merchant_id=m_view.id, query="secret")
    assert len(buyer_svc.search(q3, buyer_actor).items) == 0
    
    # Unpublish p1
    merchant_svc.unpublish_product(SetProductPublicationCommand(
        merchant_id=m_view.id, product_id=p1.id, expected_version=2, idempotency_key="pk_unpub"
    ), actor_admin)
    memory_session.commit()
    
    # Now p1 is invisible
    with pytest.raises(AppError) as exc:
        buyer_svc.get_product(m_view.id, p1.id, buyer_actor)
    assert exc.value.status_code == 404
    
    assert len(buyer_svc.search(q1, buyer_actor).items) == 0



    # Test publish product not found
    with pytest.raises(AppError) as exc:
        merchant_svc.publish_product(SetProductPublicationCommand(
            merchant_id=m_view.id, product_id="nonexistent", expected_version=1, idempotency_key="pk_pub2"
        ), actor_admin)
    assert exc.value.status_code == 404
    
    # Test unpublish product not found
    with pytest.raises(AppError) as exc:
        merchant_svc.unpublish_product(SetProductPublicationCommand(
            merchant_id=m_view.id, product_id="nonexistent", expected_version=1, idempotency_key="pk_pub3"
        ), actor_admin)
    assert exc.value.status_code == 404
    
    # Test stale write publish
    with pytest.raises(AppError) as exc:
        merchant_svc.publish_product(SetProductPublicationCommand(
            merchant_id=m_view.id, product_id=p2.id, expected_version=999, idempotency_key="pk_pub4"
        ), actor_admin)
    assert exc.value.status_code == 409

    memory_session.close()
    memory_session.get_bind().dispose()
