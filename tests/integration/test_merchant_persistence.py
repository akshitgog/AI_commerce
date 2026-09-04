"""SQLAlchemy persistence integration tests for the Merchant/Catalog domain.

These tests run against a real PostgreSQL database and are marked with
``@pytest.mark.integration`` so they are skipped when TEST_DATABASE_URL is
not set.

They verify:
1. Merchant membership can be represented safely in the database.
2. Merchant A and Merchant B data are distinguishable.
3. Duplicate SKU within one merchant is rejected by DB constraint.
4. Same SKU may exist for different merchants.
5. Money is stored as integer minor units.
6. Currency is explicit.
7. Product version is persisted.
8. Product publication status is persisted.
9. ProductMetadata fields are separate from Product commercial fields.
10. ProductImage ownership cannot escape the product/merchant relationship.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.core.errors import AppError
from ai_commerce_gateway.core.ids import new_id
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

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _test_db_url() -> str | None:
    return os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(scope="module")
def engine():  # type: ignore[no-untyped-def]
    url = _test_db_url()
    if not url:
        pytest.skip("TEST_DATABASE_URL not set — skipping PostgreSQL integration tests")
    eng = create_engine(url, pool_pre_ping=True)
    Base.metadata.create_all(eng)
    yield eng
    if eng.dialect.name == "postgresql":
        from sqlalchemy import text
        with eng.begin() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(text(f"TRUNCATE {table.name} RESTART IDENTITY CASCADE"))
    else:
        Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture
def session(engine):  # type: ignore[no-untyped-def]
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    sess = factory()
    yield sess
    sess.rollback()
    sess.close()


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


# ---------------------------------------------------------------------------
# Helper builders (create real entities via repositories)
# ---------------------------------------------------------------------------


def _create_merchant(session: Session, name: str = "Test Merchant") -> str:
    repo = SqlAlchemyMerchantRepository(session)
    merchant_id = new_id("mer")
    cmd = CreateMerchantDomain(id=merchant_id, name=name, idempotency_key=new_id("idem"))
    repo.add(cmd)
    session.commit()
    return merchant_id


def _create_product(
    session: Session,
    merchant_id: str,
    sku: str = "SKU-001",
    status: ProductStatus = ProductStatus.DRAFT,
    version: int = 1,
    price_minor: int = 10000,
    currency: str = "INR",
) -> ProductEntity:
    repo = SqlAlchemyProductRepository(session)
    now = _utc_now()
    entity = ProductEntity(
        id=new_id("prod"),
        merchant_id=merchant_id,
        sku=sku,
        title="Widget",
        description="A fine widget",
        category="Electronics",
        price=MoneyMinor(amount_minor=price_minor, currency=currency),
        available_quantity=50,
        status=status,
        version=version,
        created_at=now,
        updated_at=now,
    )
    stored = repo.add(entity)
    session.commit()
    return stored


# ---------------------------------------------------------------------------
# Correctness 1: Merchant membership can be represented safely
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMerchantMembership:
    def test_create_merchant_and_add_user(self, session: Session) -> None:
        mer_repo = SqlAlchemyMerchantRepository(session)
        user_repo = SqlAlchemyMerchantUserRepository(session)

        merchant_id = new_id("mer")
        cmd = CreateMerchantDomain(id=merchant_id, name="Alpha Shop", idempotency_key=new_id("k"))
        merchant = mer_repo.add(cmd)
        session.commit()

        user_cmd = AddMerchantUserDomain(
            id=new_id("musr"),
            merchant_id=merchant.id,
            user_id="user_alice",
            role=MerchantRole.ADMIN,
        )
        user = user_repo.add(user_cmd)
        session.commit()

        assert user.merchant_id == merchant.id
        assert user.user_id == "user_alice"
        assert user.role is MerchantRole.ADMIN

    def test_duplicate_membership_rejected_by_db(self, session: Session) -> None:
        """The (merchant_id, user_id) unique constraint is enforced by the database."""
        merchant_id = _create_merchant(session, "Dup Test Shop")
        user_repo = SqlAlchemyMerchantUserRepository(session)

        user_repo.add(
            AddMerchantUserDomain(new_id("musr"), merchant_id, "u_bob", MerchantRole.ADMIN)
        )
        session.commit()

        # Second attempt with the same user must raise (AppError wrapping IntegrityError)
        with pytest.raises((AppError, IntegrityError)):
            user_repo.add(
                AddMerchantUserDomain(new_id("musr"), merchant_id, "u_bob", MerchantRole.VIEWER)
            )

    def test_is_member_true_after_add(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Membership Shop")
        user_repo = SqlAlchemyMerchantUserRepository(session)
        user_id = "u_" + new_id("musr")
        user_repo.add(
            AddMerchantUserDomain(new_id("musr"), merchant_id, user_id, MerchantRole.EDITOR)
        )
        session.commit()
        assert user_repo.is_member(merchant_id, user_id) is True
        assert user_repo.is_member(merchant_id, "u_ghost") is False


# ---------------------------------------------------------------------------
# Correctness 2: Merchant A and B data are distinguishable
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestTenantSeparation:
    def test_merchant_a_products_not_visible_to_merchant_b(self, session: Session) -> None:
        mer_a = _create_merchant(session, "Merchant Alpha")
        mer_b = _create_merchant(session, "Merchant Beta")
        prod = _create_product(session, mer_a)

        product_repo = SqlAlchemyProductRepository(session)
        # Merchant B must not see Merchant A's product
        assert product_repo.get_by_id(mer_b, prod.id) is None
        # Merchant A can read its own
        assert product_repo.get_by_id(mer_a, prod.id) is not None

    def test_list_for_merchant_is_scoped(self, session: Session) -> None:
        mer_a = _create_merchant(session, "Scoped A")
        mer_b = _create_merchant(session, "Scoped B")
        _create_product(session, mer_a, sku="A-001")
        _create_product(session, mer_a, sku="A-002")
        _create_product(session, mer_b, sku="B-001")

        repo = SqlAlchemyProductRepository(session)
        a_list = repo.list_for_merchant(mer_a)
        b_list = repo.list_for_merchant(mer_b)

        assert all(p.merchant_id == mer_a for p in a_list)
        assert all(p.merchant_id == mer_b for p in b_list)
        assert {p.sku for p in a_list} == {"A-001", "A-002"}
        assert {p.sku for p in b_list} == {"B-001"}


# ---------------------------------------------------------------------------
# Correctness 3 & 4: SKU uniqueness
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSkuUniqueness:
    def test_duplicate_sku_same_merchant_rejected(self, session: Session) -> None:
        """DB enforces UniqueConstraint("merchant_id", "sku")."""
        merchant_id = _create_merchant(session, "SKU Shop A")
        _create_product(session, merchant_id, sku="SKU-DUP")

        product_repo = SqlAlchemyProductRepository(session)
        now = _utc_now()
        duplicate = ProductEntity(
            id=new_id("prod"),
            merchant_id=merchant_id,
            sku="SKU-DUP",  # same sku, same merchant
            title="Dupe",
            description="desc",
            category=None,
            price=MoneyMinor(amount_minor=5000, currency="INR"),
            available_quantity=1,
            status=ProductStatus.DRAFT,
            version=1,
            created_at=now,
            updated_at=now,
        )
        with pytest.raises((AppError, IntegrityError)):
            product_repo.add(duplicate)

    def test_same_sku_different_merchants_allowed(self, session: Session) -> None:
        """Same SKU for two different merchants must succeed."""
        mer_a = _create_merchant(session, "SKU MerA")
        mer_b = _create_merchant(session, "SKU MerB")
        _create_product(session, mer_a, sku="SHARED-SKU")
        _create_product(session, mer_b, sku="SHARED-SKU")  # must not raise

        repo = SqlAlchemyProductRepository(session)
        assert repo.get_by_sku(mer_a, "SHARED-SKU") is not None
        assert repo.get_by_sku(mer_b, "SHARED-SKU") is not None


# ---------------------------------------------------------------------------
# Correctness 5 & 6: Integer money and explicit currency
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMoneyStorage:
    def test_price_stored_as_integer_minor_units(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Money Shop")
        product = _create_product(session, merchant_id, price_minor=49900, currency="INR")

        repo = SqlAlchemyProductRepository(session)
        loaded = repo.get_by_id(merchant_id, product.id)
        assert loaded is not None
        assert loaded.price.amount_minor == 49900
        assert isinstance(loaded.price.amount_minor, int)

    def test_currency_stored_explicitly(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Currency Shop")
        product = _create_product(session, merchant_id, currency="USD")

        repo = SqlAlchemyProductRepository(session)
        loaded = repo.get_by_id(merchant_id, product.id)
        assert loaded is not None
        assert loaded.price.currency == "USD"

    def test_no_float_in_db_mapping(self, session: Session) -> None:
        """Regression: price_minor must come back as int, not float."""
        merchant_id = _create_merchant(session, "Float Guard Shop")
        product = _create_product(session, merchant_id, price_minor=12345, currency="INR")

        repo = SqlAlchemyProductRepository(session)
        loaded = repo.get_by_id(merchant_id, product.id)
        assert loaded is not None
        assert type(loaded.price.amount_minor) is int  # strict type check


# ---------------------------------------------------------------------------
# Correctness 7 & 8: Version and publication status
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestVersionAndStatus:
    def test_version_persisted(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Version Shop")
        product = _create_product(session, merchant_id, version=1)

        repo = SqlAlchemyProductRepository(session)
        loaded = repo.get_by_id(merchant_id, product.id)
        assert loaded is not None
        assert loaded.version == 1

    def test_version_increments_on_update(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Version Update Shop")
        product = _create_product(session, merchant_id, version=1)

        repo = SqlAlchemyProductRepository(session)
        now = _utc_now()
        updated = ProductEntity(
            id=product.id,
            merchant_id=merchant_id,
            sku=product.sku,
            title="Updated",
            description="new desc",
            category=None,
            price=product.price,
            available_quantity=product.available_quantity,
            status=product.status,
            version=2,  # ← incremented
            created_at=product.created_at,
            updated_at=now,
        )
        stored = repo.update(updated)
        session.commit()
        assert stored.version == 2

    def test_publication_status_draft(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Draft Shop")
        product = _create_product(session, merchant_id, status=ProductStatus.DRAFT)

        repo = SqlAlchemyProductRepository(session)
        loaded = repo.get_by_id(merchant_id, product.id)
        assert loaded is not None
        assert loaded.status is ProductStatus.DRAFT

    def test_publication_status_published(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Published Shop")
        product = _create_product(session, merchant_id, status=ProductStatus.PUBLISHED)

        repo = SqlAlchemyProductRepository(session)
        loaded = repo.get_by_id(merchant_id, product.id)
        assert loaded is not None
        assert loaded.status is ProductStatus.PUBLISHED

    def test_only_published_visible_in_buyer_list(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Buyer Vis Shop")
        _create_product(session, merchant_id, sku="DRAFT-1", status=ProductStatus.DRAFT)
        _create_product(session, merchant_id, sku="PUB-1", status=ProductStatus.PUBLISHED)
        _create_product(session, merchant_id, sku="UNPUB-1", status=ProductStatus.UNPUBLISHED)

        repo = SqlAlchemyProductRepository(session)
        published = repo.list_published(merchant_id)
        assert len(published) == 1
        assert published[0].sku == "PUB-1"


# ---------------------------------------------------------------------------
# Correctness 9: ProductMetadata separation
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestProductMetadataSeparation:
    def test_metadata_is_separate_table(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Metadata Shop")
        product = _create_product(session, merchant_id, sku="META-001")

        meta_repo = SqlAlchemyProductMetadataRepository(session)
        meta = ProductMetadataEntity(
            product_id=product.id,
            tags=("gadget", "sale"),
            attributes={"colour": "blue"},
            search_text="blue gadget sale",
            source="AI",
            review_status=ReviewStatus.PENDING,
            updated_at=_utc_now(),
        )
        stored_meta = meta_repo.upsert(merchant_id, meta)
        session.commit()

        # ProductMetadata has no price/currency/quantity/status/version
        assert not hasattr(stored_meta, "price_minor")
        assert not hasattr(stored_meta, "currency")
        assert not hasattr(stored_meta, "available_quantity")
        assert not hasattr(stored_meta, "status")
        assert not hasattr(stored_meta, "version")

    def test_ai_metadata_does_not_change_product_price(self, session: Session) -> None:
        """AI metadata upsert must not touch the product's commercial fields."""
        merchant_id = _create_merchant(session, "Price Guard Shop")
        product = _create_product(session, merchant_id, price_minor=99900, currency="INR")

        meta_repo = SqlAlchemyProductMetadataRepository(session)
        # Simulate AI enrichment
        meta = ProductMetadataEntity(
            product_id=product.id,
            tags=("luxury",),
            attributes={"material": "gold"},
            search_text="luxury gold item",
            source="AI",
            review_status=ReviewStatus.PENDING,
            updated_at=_utc_now(),
        )
        meta_repo.upsert(merchant_id, meta)
        session.commit()

        # The product price must remain unchanged
        product_repo = SqlAlchemyProductRepository(session)
        reloaded = product_repo.get_by_id(merchant_id, product.id)
        assert reloaded is not None
        assert reloaded.price.amount_minor == 99900
        assert reloaded.price.currency == "INR"

    def test_metadata_review_status_persisted(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Review Status Shop")
        product = _create_product(session, merchant_id, sku="REV-001")

        meta_repo = SqlAlchemyProductMetadataRepository(session)
        meta = ProductMetadataEntity(
            product_id=product.id,
            tags=(),
            attributes={},
            search_text=None,
            source="AI",
            review_status=ReviewStatus.PENDING,
            updated_at=_utc_now(),
        )
        meta_repo.upsert(merchant_id, meta)
        session.commit()

        loaded = meta_repo.get(merchant_id, product.id)
        assert loaded is not None
        assert loaded.review_status is ReviewStatus.PENDING


# ---------------------------------------------------------------------------
# Correctness 10: ProductImage ownership invariants
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestProductImageOwnership:
    def test_image_created_with_merchant_and_product_scope(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Image Shop")
        product = _create_product(session, merchant_id, sku="IMG-001")

        image_repo = SqlAlchemyProductImageRepository(session)
        img = ProductImageEntity(
            id=new_id("pimg"),
            merchant_id=merchant_id,
            product_id=product.id,
            storage_path=f"images/{merchant_id}/{product.id}/0.jpg",
            public_url=None,
            alt_text="Front view",
            sort_order=0,
            created_at=_utc_now(),
        )
        stored = image_repo.add(img)
        session.commit()

        assert stored.merchant_id == merchant_id
        assert stored.product_id == product.id

    def test_image_not_accessible_cross_merchant(self, session: Session) -> None:
        """Correctness 10: Image ownership cannot escape the merchant."""
        mer_a = _create_merchant(session, "Image Merchant A")
        mer_b = _create_merchant(session, "Image Merchant B")
        product_a = _create_product(session, mer_a, sku="IA-001")

        image_repo = SqlAlchemyProductImageRepository(session)
        img = ProductImageEntity(
            id=new_id("pimg"),
            merchant_id=mer_a,
            product_id=product_a.id,
            storage_path=f"images/{mer_a}/{product_a.id}/0.jpg",
            public_url=None,
            alt_text=None,
            sort_order=0,
            created_at=_utc_now(),
        )
        stored = image_repo.add(img)
        session.commit()

        # Merchant B must not see Merchant A's image
        assert image_repo.get(mer_b, product_a.id, stored.id) is None
        # Merchant A can see its own image
        assert image_repo.get(mer_a, product_a.id, stored.id) is not None

    def test_duplicate_sort_order_same_product_rejected(self, session: Session) -> None:
        """UniqueConstraint("product_id", "sort_order") enforced by DB."""
        merchant_id = _create_merchant(session, "Dup Sort Shop")
        product = _create_product(session, merchant_id, sku="DUPIMG-001")

        image_repo = SqlAlchemyProductImageRepository(session)
        img1 = ProductImageEntity(
            id=new_id("pimg"),
            merchant_id=merchant_id,
            product_id=product.id,
            storage_path=f"images/{merchant_id}/{product.id}/s0_a.jpg",
            public_url=None,
            alt_text=None,
            sort_order=0,
            created_at=_utc_now(),
        )
        image_repo.add(img1)
        session.commit()

        img2 = ProductImageEntity(
            id=new_id("pimg"),
            merchant_id=merchant_id,
            product_id=product.id,
            storage_path=f"images/{merchant_id}/{product.id}/s0_b.jpg",
            public_url=None,
            alt_text=None,
            sort_order=0,  # same sort_order
            created_at=_utc_now(),
        )
        with pytest.raises((AppError, IntegrityError)):
            image_repo.add(img2)

    def test_list_images_ordered_by_sort_order(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Ordered Image Shop")
        product = _create_product(session, merchant_id, sku="ORD-IMG-001")

        image_repo = SqlAlchemyProductImageRepository(session)
        for sort_order in (2, 0, 1):
            img = ProductImageEntity(
                id=new_id("pimg"),
                merchant_id=merchant_id,
                product_id=product.id,
                storage_path=f"images/{merchant_id}/{product.id}/{sort_order}.jpg",
                public_url=None,
                alt_text=None,
                sort_order=sort_order,
                created_at=_utc_now(),
            )
            image_repo.add(img)
            session.commit()

        images = image_repo.list_for_product(merchant_id, product.id)
        assert [i.sort_order for i in images] == [0, 1, 2]

    def test_delete_image_with_correct_tenant(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Delete Image Shop")
        product = _create_product(session, merchant_id, sku="DEL-IMG-001")

        image_repo = SqlAlchemyProductImageRepository(session)
        img = ProductImageEntity(
            id=new_id("pimg"),
            merchant_id=merchant_id,
            product_id=product.id,
            storage_path=f"images/{merchant_id}/{product.id}/del.jpg",
            public_url=None,
            alt_text=None,
            sort_order=0,
            created_at=_utc_now(),
        )
        stored = image_repo.add(img)
        session.commit()

        image_repo.delete(merchant_id, product.id, stored.id)
        session.commit()

        assert image_repo.get(merchant_id, product.id, stored.id) is None


# ---------------------------------------------------------------------------
# MerchantPolicy persistence
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestMerchantPolicyPersistence:
    def test_manual_all_policy_persisted(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Policy Shop")
        policy_repo = SqlAlchemyMerchantPolicyRepository(session)
        now = _utc_now()
        policy = MerchantPolicyEntity(
            id=new_id("pol"),
            merchant_id=merchant_id,
            mode=PolicyMode.MANUAL_ALL,
            auto_accept_max=None,
            version=1,
            status=RecordStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        policy_repo.add(policy)
        session.commit()

        loaded = policy_repo.get_active(merchant_id)
        assert loaded is not None
        assert loaded.mode is PolicyMode.MANUAL_ALL
        assert loaded.auto_accept_max is None
        assert loaded.version == 1

    def test_auto_below_limit_policy_persisted(self, session: Session) -> None:
        merchant_id = _create_merchant(session, "Auto Policy Shop")
        policy_repo = SqlAlchemyMerchantPolicyRepository(session)
        now = _utc_now()
        policy = MerchantPolicyEntity(
            id=new_id("pol"),
            merchant_id=merchant_id,
            mode=PolicyMode.AUTO_BELOW_LIMIT,
            auto_accept_max=MoneyMinor(amount_minor=50000, currency="INR"),
            version=1,
            status=RecordStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        policy_repo.add(policy)
        session.commit()

        loaded = policy_repo.get_active(merchant_id)
        assert loaded is not None
        assert loaded.mode is PolicyMode.AUTO_BELOW_LIMIT
        assert loaded.auto_accept_max is not None
        assert loaded.auto_accept_max.amount_minor == 50000
        assert loaded.auto_accept_max.currency == "INR"

    def test_policy_get_active_scoped_to_merchant(self, session: Session) -> None:
        mer_a = _create_merchant(session, "Policy Isolation A")
        mer_b = _create_merchant(session, "Policy Isolation B")
        policy_repo = SqlAlchemyMerchantPolicyRepository(session)
        now = _utc_now()

        policy_repo.add(
            MerchantPolicyEntity(
                id=new_id("pol"),
                merchant_id=mer_a,
                mode=PolicyMode.MANUAL_ALL,
                auto_accept_max=None,
                version=1,
                status=RecordStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()

        # Merchant B has no policy
        assert policy_repo.get_active(mer_b) is None
        # Merchant A does
        assert policy_repo.get_active(mer_a) is not None
