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
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session_local()
    yield session
    session.close()
    engine.dispose()


def test_buyer_catalog_service_draft_invisibility_and_publication_lifecycle(
    memory_session,
):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    merchant_svc = ApplicationMerchantCatalogService(m_repo, p_repo)
    buyer_svc = ApplicationCatalogService(p_repo)

    sys_actor = ActorContext(
        actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id="cor1"
    )
    m_view = merchant_svc.create_merchant(
        CreateMerchantCommand(name="M_Buyer", idempotency_key="ik"), sys_actor
    )
    memory_session.commit()

    actor_admin = ActorContext(
        actor_id="u1",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m_view.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id="cor1",
    )
    buyer_actor = ActorContext(
        actor_id="buyer1", actor_type=ActorType.BUYER, correlation_id="cor2"
    )

    # Create two products, one published and one draft
    p1 = merchant_svc.create_product(
        CreateProductCommand(
            merchant_id=m_view.id,
            sku="SKU1",
            title="Published Item",
            description="A great item with detailed description",
            category="electronics",
            price=Money(amount_minor=500, currency="USD"),
            available_quantity=10,
            idempotency_key="pk1",
        ),
        actor_admin,
    )
    p2 = merchant_svc.create_product(
        CreateProductCommand(
            merchant_id=m_view.id,
            sku="SKU2",
            title="Draft Item",
            description="Secret unpublished item",
            category="books",
            price=Money(amount_minor=1000, currency="USD"),
            available_quantity=5,
            idempotency_key="pk2",
        ),
        actor_admin,
    )
    memory_session.commit()

    # Publish p1
    merchant_svc.publish_product(
        SetProductPublicationCommand(
            merchant_id=m_view.id,
            product_id=p1.id,
            expected_version=1,
            idempotency_key="pk_pub",
        ),
        actor_admin,
    )
    memory_session.commit()

    # Draft item is invisible to buyers (404)
    with pytest.raises(AppError) as exc:
        buyer_svc.get_product(m_view.id, p2.id, buyer_actor)
    assert exc.value.status_code == 404

    # Published item is visible to buyers
    res = buyer_svc.get_product(m_view.id, p1.id, buyer_actor)
    assert res.id == p1.id

    # Search returns only published items
    q1 = CatalogSearchQuery(merchant_id=m_view.id)
    search_res = buyer_svc.search(q1, buyer_actor)
    assert len(search_res.items) == 1
    assert search_res.items[0].id == p1.id

    # Unpublish p1 -> immediately invisible
    merchant_svc.unpublish_product(
        SetProductPublicationCommand(
            merchant_id=m_view.id,
            product_id=p1.id,
            expected_version=2,
            idempotency_key="pk_unpub",
        ),
        actor_admin,
    )
    memory_session.commit()

    with pytest.raises(AppError) as exc:
        buyer_svc.get_product(m_view.id, p1.id, buyer_actor)
    assert exc.value.status_code == 404
    assert len(buyer_svc.search(q1, buyer_actor).items) == 0


def test_publish_unpublish_role_and_tenant_denials(memory_session):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    merchant_svc = ApplicationMerchantCatalogService(m_repo, p_repo)

    sys_actor = ActorContext(
        actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id="cor1"
    )
    m1 = merchant_svc.create_merchant(
        CreateMerchantCommand(name="M1", idempotency_key="ik1"), sys_actor
    )
    m2 = merchant_svc.create_merchant(
        CreateMerchantCommand(name="M2", idempotency_key="ik2"), sys_actor
    )
    memory_session.commit()

    actor_admin = ActorContext(
        actor_id="u1",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m1.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id="cor1",
    )
    actor_viewer = ActorContext(
        actor_id="u_view",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m1.id]),
        roles=frozenset([MerchantRole.VIEWER]),
        correlation_id="cor2",
    )
    actor_other_merchant = ActorContext(
        actor_id="u_other",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m2.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id="cor3",
    )

    prod = merchant_svc.create_product(
        CreateProductCommand(
            merchant_id=m1.id,
            sku="SKU-DENY",
            title="Prod",
            description="Test description",
            price=Money(amount_minor=100, currency="USD"),
            available_quantity=5,
            idempotency_key="p_create",
        ),
        actor_admin,
    )
    memory_session.commit()

    # VIEWER denied publish (403)
    cmd_pub = SetProductPublicationCommand(
        merchant_id=m1.id,
        product_id=prod.id,
        expected_version=1,
        idempotency_key="p_pub_deny1",
    )
    with pytest.raises(AppError) as exc_v:
        merchant_svc.publish_product(cmd_pub, actor_viewer)
    assert exc_v.value.status_code == 403

    # Cross-tenant actor denied publish (403)
    with pytest.raises(AppError) as exc_ct:
        merchant_svc.publish_product(cmd_pub, actor_other_merchant)
    assert exc_ct.value.status_code == 403

    # Admin successfully publishes
    merchant_svc.publish_product(cmd_pub, actor_admin)
    memory_session.commit()

    # VIEWER denied unpublish (403)
    cmd_unpub = SetProductPublicationCommand(
        merchant_id=m1.id,
        product_id=prod.id,
        expected_version=2,
        idempotency_key="p_unpub_deny",
    )
    with pytest.raises(AppError) as exc_v_unpub:
        merchant_svc.unpublish_product(cmd_unpub, actor_viewer)
    assert exc_v_unpub.value.status_code == 403

    # Cross-tenant actor denied unpublish (403)
    with pytest.raises(AppError) as exc_ct_unpub:
        merchant_svc.unpublish_product(cmd_unpub, actor_other_merchant)
    assert exc_ct_unpub.value.status_code == 403


def test_publish_unpublish_stale_write_and_not_found(memory_session):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    merchant_svc = ApplicationMerchantCatalogService(m_repo, p_repo)

    sys_actor = ActorContext(
        actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id="cor1"
    )
    m = merchant_svc.create_merchant(
        CreateMerchantCommand(name="M_Stale", idempotency_key="ik_stale"), sys_actor
    )
    memory_session.commit()

    actor_admin = ActorContext(
        actor_id="u1",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id="cor1",
    )
    prod = merchant_svc.create_product(
        CreateProductCommand(
            merchant_id=m.id,
            sku="SKU-STALE",
            title="Prod",
            description="Stale test description",
            price=Money(amount_minor=100, currency="USD"),
            available_quantity=5,
            idempotency_key="p_create_stale",
        ),
        actor_admin,
    )
    memory_session.commit()

    # Nonexistent product on publish -> 404
    with pytest.raises(AppError) as exc_nf_pub:
        merchant_svc.publish_product(
            SetProductPublicationCommand(
                merchant_id=m.id,
                product_id="nonexistent_id",
                expected_version=1,
                idempotency_key="p_pub_nf",
            ),
            actor_admin,
        )
    assert exc_nf_pub.value.status_code == 404

    # Nonexistent product on unpublish -> 404
    with pytest.raises(AppError) as exc_nf_unpub:
        merchant_svc.unpublish_product(
            SetProductPublicationCommand(
                merchant_id=m.id,
                product_id="nonexistent_id",
                expected_version=1,
                idempotency_key="p_unpub_nf",
            ),
            actor_admin,
        )
    assert exc_nf_unpub.value.status_code == 404

    # Stale version publish -> 409
    with pytest.raises(AppError) as exc_stale_pub:
        merchant_svc.publish_product(
            SetProductPublicationCommand(
                merchant_id=m.id,
                product_id=prod.id,
                expected_version=99,
                idempotency_key="p_pub_stale",
            ),
            actor_admin,
        )
    assert exc_stale_pub.value.status_code == 409

    # Successful publish
    merchant_svc.publish_product(
        SetProductPublicationCommand(
            merchant_id=m.id,
            product_id=prod.id,
            expected_version=1,
            idempotency_key="p_pub_ok",
        ),
        actor_admin,
    )
    memory_session.commit()

    # Stale version unpublish -> 409
    with pytest.raises(AppError) as exc_stale_unpub:
        merchant_svc.unpublish_product(
            SetProductPublicationCommand(
                merchant_id=m.id,
                product_id=prod.id,
                expected_version=1,  # expected is 2 after publish
                idempotency_key="p_unpub_stale",
            ),
            actor_admin,
        )
    assert exc_stale_unpub.value.status_code == 409


def test_catalog_search_filters_and_multi_merchant_isolation(memory_session):
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    p_repo = SqlAlchemyProductRepository(memory_session)
    merchant_svc = ApplicationMerchantCatalogService(m_repo, p_repo)
    buyer_svc = ApplicationCatalogService(p_repo)

    sys_actor = ActorContext(
        actor_id="sys1", actor_type=ActorType.SYSTEM, correlation_id="cor1"
    )
    m1 = merchant_svc.create_merchant(
        CreateMerchantCommand(name="M1", idempotency_key="ik_m1"), sys_actor
    )
    m2 = merchant_svc.create_merchant(
        CreateMerchantCommand(name="M2", idempotency_key="ik_m2"), sys_actor
    )
    memory_session.commit()

    admin_m1 = ActorContext(
        actor_id="u_m1",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m1.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id="c1",
    )
    admin_m2 = ActorContext(
        actor_id="u_m2",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset([m2.id]),
        roles=frozenset([MerchantRole.ADMIN]),
        correlation_id="c2",
    )
    buyer_actor = ActorContext(
        actor_id="buyer1", actor_type=ActorType.BUYER, correlation_id="b1"
    )

    # Populate M1 with multiple published items
    p1 = merchant_svc.create_product(
        CreateProductCommand(
            merchant_id=m1.id,
            sku="SKU-PHONE",
            title="Smart Phone Pro",
            description="High-end cellular device with OLED screen",
            category="electronics",
            price=Money(amount_minor=100000, currency="USD"),
            available_quantity=10,
            idempotency_key="ik_p1",
        ),
        admin_m1,
    )
    p2 = merchant_svc.create_product(
        CreateProductCommand(
            merchant_id=m1.id,
            sku="SKU-BOOK",
            title="Programming Python",
            description="Comprehensive guide to python development",
            category="books",
            price=Money(amount_minor=4000, currency="USD"),
            available_quantity=50,
            idempotency_key="ik_p2",
        ),
        admin_m1,
    )
    p3 = merchant_svc.create_product(
        CreateProductCommand(
            merchant_id=m1.id,
            sku="SKU-HEADPHONES",
            title="Wireless Headphones",
            description="Noise canceling audio headphones",
            category="electronics",
            price=Money(amount_minor=25000, currency="USD"),
            available_quantity=20,
            idempotency_key="ik_p3",
        ),
        admin_m1,
    )
    # Populate M2 with a published item
    p_m2 = merchant_svc.create_product(
        CreateProductCommand(
            merchant_id=m2.id,
            sku="SKU-M2-ITEM",
            title="M2 Exclusive Phone",
            description="Only for merchant 2",
            category="electronics",
            price=Money(amount_minor=50000, currency="USD"),
            available_quantity=10,
            idempotency_key="ik_m2_p",
        ),
        admin_m2,
    )
    memory_session.commit()

    # Publish all
    for p, actor, mid in [
        (p1, admin_m1, m1.id),
        (p2, admin_m1, m1.id),
        (p3, admin_m1, m1.id),
        (p_m2, admin_m2, m2.id),
    ]:
        merchant_svc.publish_product(
            SetProductPublicationCommand(
                merchant_id=mid,
                product_id=p.id,
                expected_version=1,
                idempotency_key=f"pub_{p.id}",
            ),
            actor,
        )
    memory_session.commit()

    # 1. Multi-merchant isolation: Search on M1 never returns M2's product
    res_m1 = buyer_svc.search(CatalogSearchQuery(merchant_id=m1.id), buyer_actor)
    assert len(res_m1.items) == 3
    assert all(item.merchant_id == m1.id for item in res_m1.items)
    assert all(item.id != p_m2.id for item in res_m1.items)

    # Search on M2 returns only M2's product
    res_m2 = buyer_svc.search(CatalogSearchQuery(merchant_id=m2.id), buyer_actor)
    assert len(res_m2.items) == 1
    assert res_m2.items[0].id == p_m2.id

    # Cross-tenant get_product is denied (404)
    with pytest.raises(AppError) as exc_cross:
        buyer_svc.get_product(m1.id, p_m2.id, buyer_actor)
    assert exc_cross.value.status_code == 404

    # 2. Query filter on description
    res_desc = buyer_svc.search(
        CatalogSearchQuery(merchant_id=m1.id, query="OLED"), buyer_actor
    )
    assert len(res_desc.items) == 1
    assert res_desc.items[0].id == p1.id

    # 3. Category filter
    res_cat = buyer_svc.search(
        CatalogSearchQuery(merchant_id=m1.id, category="books"), buyer_actor
    )
    assert len(res_cat.items) == 1
    assert res_cat.items[0].id == p2.id

    # Category mismatch returns empty
    res_cat_empty = buyer_svc.search(
        CatalogSearchQuery(merchant_id=m1.id, category="furniture"), buyer_actor
    )
    assert len(res_cat_empty.items) == 0

    # 4. Price range filters
    # min_price_minor
    res_min_price = buyer_svc.search(
        CatalogSearchQuery(merchant_id=m1.id, min_price_minor=30000), buyer_actor
    )
    assert len(res_min_price.items) == 1
    assert res_min_price.items[0].id == p1.id

    # max_price_minor
    res_max_price = buyer_svc.search(
        CatalogSearchQuery(merchant_id=m1.id, max_price_minor=10000), buyer_actor
    )
    assert len(res_max_price.items) == 1
    assert res_max_price.items[0].id == p2.id

    # Combined price range
    res_range = buyer_svc.search(
        CatalogSearchQuery(
            merchant_id=m1.id, min_price_minor=10000, max_price_minor=30000
        ),
        buyer_actor,
    )
    assert len(res_range.items) == 1
    assert res_range.items[0].id == p3.id

    # 5. Currency filter match & mismatch
    res_curr_match = buyer_svc.search(
        CatalogSearchQuery(merchant_id=m1.id, currency="USD"), buyer_actor
    )
    assert len(res_curr_match.items) == 3

    res_curr_mismatch = buyer_svc.search(
        CatalogSearchQuery(merchant_id=m1.id, currency="EUR"), buyer_actor
    )
    assert len(res_curr_mismatch.items) == 0

    # 6. Pagination testing with next_cursor
    res_page1 = buyer_svc.search(
        CatalogSearchQuery(merchant_id=m1.id, limit=2), buyer_actor
    )
    assert len(res_page1.items) == 2
    assert res_page1.next_cursor is not None

    res_page2 = buyer_svc.search(
        CatalogSearchQuery(merchant_id=m1.id, cursor=res_page1.next_cursor, limit=2),
        buyer_actor,
    )
    assert len(res_page2.items) == 1
    # Items on page 2 do not overlap with page 1
    page1_ids = {item.id for item in res_page1.items}
    assert res_page2.items[0].id not in page1_ids
