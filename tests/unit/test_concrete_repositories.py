from dataclasses import replace
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.core.errors import AppError
from ai_commerce_gateway.domain.enums import (
    MerchantRole,
    PolicyMode,
    ProductStatus,
    RecordStatus,
    ReviewStatus,
)
from ai_commerce_gateway.domain.merchant import AddMerchantUserDomain, CreateMerchantDomain
from ai_commerce_gateway.domain.policy import MerchantPolicyEntity
from ai_commerce_gateway.domain.product import (
    MoneyMinor,
    ProductEntity,
    ProductImageEntity,
    ProductMetadataEntity,
)
from ai_commerce_gateway.infrastructure.database.merchant_repositories import (
    SqlAlchemyMerchantPolicyRepository,
    SqlAlchemyMerchantRepository,
    SqlAlchemyMerchantUserRepository,
    SqlAlchemyProductImageRepository,
    SqlAlchemyProductMetadataRepository,
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


def _now() -> datetime:
    return datetime.now(tz=UTC)


def test_merchant_repo_untested_branches(memory_session: Session) -> None:
    repo = SqlAlchemyMerchantRepository(memory_session)
    assert repo.get_by_id("non_existent") is None
    assert repo.exists("non_existent") is False

    m = CreateMerchantDomain(id="m1", name="M1", idempotency_key="ik1")
    repo.add(m)
    memory_session.commit()

    assert repo.exists("m1") is True

    with pytest.raises(AppError) as exc_info:
        repo.add(m)
    assert exc_info.value.status_code == 409
    memory_session.rollback()


def test_merchant_user_repo_list(memory_session: Session) -> None:
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    m_repo.add(CreateMerchantDomain(id="m1", name="M1", idempotency_key="ik1"))

    u_repo = SqlAlchemyMerchantUserRepository(memory_session)
    u_repo.add(
        AddMerchantUserDomain(id="mu1", merchant_id="m1", user_id="u1", role=MerchantRole.ADMIN)
    )  # noqa: E501
    u_repo.add(
        AddMerchantUserDomain(id="mu2", merchant_id="m1", user_id="u2", role=MerchantRole.VIEWER)
    )  # noqa: E501
    memory_session.commit()

    users = u_repo.list_for_merchant("m1")
    assert len(users) == 2
    assert users[0].user_id == "u1"
    assert users[1].user_id == "u2"


def test_product_repo_branches(memory_session: Session) -> None:
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    m_repo.add(CreateMerchantDomain(id="m1", name="M1", idempotency_key="ik1"))

    p_repo = SqlAlchemyProductRepository(memory_session)
    assert p_repo.sku_exists_for_merchant("m1", "SKU1") is False

    p1 = ProductEntity(
        id="p1",
        merchant_id="m1",
        sku="SKU1",
        title="T1",
        description="D1",
        category=None,
        price=MoneyMinor(100, "USD"),
        available_quantity=10,
        status=ProductStatus.DRAFT,
        version=1,  # noqa: E501
        created_at=_now(),
        updated_at=_now(),
    )
    p_repo.add(p1)

    p2 = ProductEntity(
        id="p2",
        merchant_id="m1",
        sku="SKU2",
        title="T2",
        description="D2",
        category=None,
        price=MoneyMinor(100, "USD"),
        available_quantity=10,
        status=ProductStatus.PUBLISHED,
        version=1,  # noqa: E501
        created_at=_now(),
        updated_at=_now(),
    )
    p_repo.add(p2)
    memory_session.commit()

    assert p_repo.sku_exists_for_merchant("m1", "SKU1") is True

    p3 = ProductEntity(
        id="p_non",
        merchant_id="m1",
        sku="SKU3",
        title="T3",
        description="D",
        category=None,
        price=MoneyMinor(100, "USD"),
        available_quantity=10,
        status=ProductStatus.DRAFT,
        version=1,
        created_at=_now(),
        updated_at=_now(),
    )
    with pytest.raises(AppError) as exc_info:
        p_repo.update(p3)
    assert exc_info.value.status_code == 404
    memory_session.rollback()

    p1_updated = replace(p1, sku="SKU2")
    with pytest.raises(AppError) as exc_info:
        p_repo.update(p1_updated)
    assert exc_info.value.status_code == 409
    memory_session.rollback()

    items = p_repo.list_for_merchant("m1", limit=1)
    assert len(items) == 1
    items2 = p_repo.list_for_merchant("m1", cursor=items[0].id, limit=1)
    assert len(items2) == 1

    pubs = p_repo.list_published("m1", limit=10)
    assert len(pubs) == 1
    assert pubs[0].id == "p2"


def test_metadata_repo_tenant_isolation(memory_session: Session) -> None:
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    m_repo.add(CreateMerchantDomain(id="m1", name="M1", idempotency_key="ik1"))
    m_repo.add(CreateMerchantDomain(id="m2", name="M2", idempotency_key="ik2"))

    p_repo = SqlAlchemyProductRepository(memory_session)
    p = ProductEntity(
        id="p1",
        merchant_id="m1",
        sku="SKU1",
        title="T1",
        description="D",
        category=None,
        price=MoneyMinor(100, "USD"),
        available_quantity=10,
        status=ProductStatus.DRAFT,
        version=1,
        created_at=_now(),
        updated_at=_now(),
    )
    p_repo.add(p)
    memory_session.commit()

    meta_repo = SqlAlchemyProductMetadataRepository(memory_session)

    meta = ProductMetadataEntity(
        product_id="p1",
        tags=("evil",),
        attributes={},
        search_text=None,
        source="AI",
        review_status=ReviewStatus.PENDING,
        updated_at=_now(),  # noqa: E501
    )
    with pytest.raises(AppError) as exc_info:
        meta_repo.upsert("m2", meta)
    assert exc_info.value.status_code == 404

    meta_repo.upsert("m1", meta)
    memory_session.commit()

    meta2 = ProductMetadataEntity(
        product_id="p1",
        tags=("evil2",),
        attributes={},
        search_text=None,
        source="AI",
        review_status=ReviewStatus.PENDING,
        updated_at=_now(),  # noqa: E501
    )
    res = meta_repo.upsert("m1", meta2)
    memory_session.commit()
    assert res.tags == ("evil2",)


def test_image_repo_isolation_and_count(memory_session: Session) -> None:
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    m_repo.add(CreateMerchantDomain(id="m1", name="M1", idempotency_key="ik1"))
    m_repo.add(CreateMerchantDomain(id="m2", name="M2", idempotency_key="ik2"))

    p_repo = SqlAlchemyProductRepository(memory_session)
    p = ProductEntity(
        id="p1",
        merchant_id="m1",
        sku="SKU1",
        title="T1",
        description="D",
        category=None,
        price=MoneyMinor(100, "USD"),
        available_quantity=10,
        status=ProductStatus.DRAFT,
        version=1,
        created_at=_now(),
        updated_at=_now(),
    )
    p_repo.add(p)
    memory_session.commit()

    img_repo = SqlAlchemyProductImageRepository(memory_session)
    img = ProductImageEntity(
        id="i1",
        merchant_id="m2",
        product_id="p1",
        storage_path="path",
        public_url=None,
        alt_text=None,
        sort_order=0,
        created_at=_now(),  # noqa: E501
    )
    with pytest.raises(AppError) as exc_info:
        img_repo.add(img)
    assert exc_info.value.status_code == 404
    memory_session.rollback()

    img_m1 = replace(img, merchant_id="m1")
    img_repo.add(img_m1)
    memory_session.commit()

    assert img_repo.count_for_product("m1", "p1") == 1


def test_policy_repo_update_and_errors(memory_session: Session) -> None:
    m_repo = SqlAlchemyMerchantRepository(memory_session)
    m_repo.add(CreateMerchantDomain(id="m1", name="M1", idempotency_key="ik1"))
    memory_session.commit()

    pol_repo = SqlAlchemyMerchantPolicyRepository(memory_session)
    pol = MerchantPolicyEntity(
        id="pol1",
        merchant_id="m1",
        mode=PolicyMode.MANUAL_ALL,
        auto_accept_max=None,
        version=1,
        status=RecordStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),  # noqa: E501
    )
    pol_repo.add(pol)
    memory_session.commit()

    pol_dup = MerchantPolicyEntity(
        id="pol2",
        merchant_id="m1",
        mode=PolicyMode.MANUAL_ALL,
        auto_accept_max=None,
        version=1,
        status=RecordStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),  # noqa: E501
    )
    with pytest.raises(AppError) as exc_info:
        pol_repo.add(pol_dup)
    assert exc_info.value.status_code == 409
    memory_session.rollback()

    pol_not_found = MerchantPolicyEntity(
        id="pol_no",
        merchant_id="m1",
        mode=PolicyMode.MANUAL_ALL,
        auto_accept_max=None,
        version=2,
        status=RecordStatus.ACTIVE,
        created_at=_now(),
        updated_at=_now(),  # noqa: E501
    )
    with pytest.raises(AppError) as exc_info:
        pol_repo.update(pol_not_found)
    assert exc_info.value.status_code == 404

    pol_updated = replace(pol, version=2)
    pol_repo.update(pol_updated)
    memory_session.commit()

    pol_inactive = replace(pol_updated, status=RecordStatus.INACTIVE)
    res = pol_repo.update(pol_inactive)
    assert res.status == RecordStatus.INACTIVE
