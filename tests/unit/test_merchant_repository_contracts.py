"""Repository interface/contract tests using in-memory fakes.

These tests verify that the repository Protocol contracts behave correctly
without requiring a database connection.  They use simple dict-based fakes
that implement the same Protocol interface.

Each fake's behavior mimics what the database constraint will enforce so that
the contract tests describe *what* the repository must guarantee, independent
of the SQLAlchemy implementation tested separately.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_commerce_gateway.domain.enums import (
    MerchantRole,
    ProductStatus,
)
from ai_commerce_gateway.domain.merchant import (
    AddMerchantUserDomain,
    CreateMerchantDomain,
    MerchantEntity,
    MerchantUserEntity,
)
from ai_commerce_gateway.domain.product import (
    MoneyMinor,
    ProductEntity,
    ProductImageEntity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _make_product(
    product_id: str = "prod_1",
    merchant_id: str = "mer_a",
    sku: str = "SKU-001",
    status: ProductStatus = ProductStatus.DRAFT,
    version: int = 1,
) -> ProductEntity:
    now = _utc_now()
    return ProductEntity(
        id=product_id,
        merchant_id=merchant_id,
        sku=sku,
        title="Test Product",
        description="desc",
        category=None,
        price=MoneyMinor(amount_minor=10000, currency="INR"),
        available_quantity=10,
        status=status,
        version=version,
        created_at=now,
        updated_at=now,
    )


def _make_image(
    image_id: str = "pimg_1",
    merchant_id: str = "mer_a",
    product_id: str = "prod_1",
    sort_order: int = 0,
) -> ProductImageEntity:
    return ProductImageEntity(
        id=image_id,
        merchant_id=merchant_id,
        product_id=product_id,
        storage_path=f"path/{merchant_id}/{product_id}/{sort_order}.jpg",
        public_url=None,
        alt_text=None,
        sort_order=sort_order,
        created_at=_utc_now(),
    )


# ---------------------------------------------------------------------------
# In-memory fakes
# ---------------------------------------------------------------------------


class FakeMerchantRepository:
    """In-memory fake satisfying MerchantRepository Protocol."""

    def __init__(self) -> None:
        self._store: dict[str, MerchantEntity] = {}

    def add(self, domain: CreateMerchantDomain) -> MerchantEntity:
        if domain.id in self._store:
            raise ValueError("duplicate merchant id")
        now = _utc_now()
        entity = MerchantEntity(
            id=domain.id,
            name=domain.name,
            status=domain.status,
            created_at=now,
            updated_at=now,
        )
        self._store[domain.id] = entity
        return entity

    def get_by_id(self, merchant_id: str) -> MerchantEntity | None:
        return self._store.get(merchant_id)

    def exists(self, merchant_id: str) -> bool:
        return merchant_id in self._store


class FakeMerchantUserRepository:
    """In-memory fake satisfying MerchantUserRepository Protocol."""

    def __init__(self) -> None:
        # keyed (merchant_id, user_id) → entity
        self._store: dict[tuple[str, str], MerchantUserEntity] = {}

    def add(self, domain: AddMerchantUserDomain) -> MerchantUserEntity:
        key = (domain.merchant_id, domain.user_id)
        if key in self._store:
            raise ValueError("duplicate membership")  # mirrors DB unique constraint
        entity = MerchantUserEntity(
            id=domain.id,
            merchant_id=domain.merchant_id,
            user_id=domain.user_id,
            role=domain.role,
            created_at=_utc_now(),
        )
        self._store[key] = entity
        return entity

    def get(self, merchant_id: str, user_id: str) -> MerchantUserEntity | None:
        return self._store.get((merchant_id, user_id))

    def list_for_merchant(self, merchant_id: str) -> list[MerchantUserEntity]:
        return [e for e in self._store.values() if e.merchant_id == merchant_id]

    def is_member(self, merchant_id: str, user_id: str) -> bool:
        return (merchant_id, user_id) in self._store


class FakeProductRepository:
    """In-memory fake satisfying ProductRepository Protocol.

    Enforces (merchant_id, sku) uniqueness and merchant-scoped queries.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, ProductEntity] = {}
        self._sku_index: dict[tuple[str, str], str] = {}  # (merchant_id, sku) → product_id

    def add(self, entity: ProductEntity) -> ProductEntity:
        sku_key = (entity.merchant_id, entity.sku)
        if sku_key in self._sku_index:
            raise ValueError(
                f"SKU {entity.sku!r} already exists for merchant {entity.merchant_id!r}"
            )
        self._by_id[entity.id] = entity
        self._sku_index[sku_key] = entity.id
        return entity

    def get_by_id(self, merchant_id: str, product_id: str) -> ProductEntity | None:
        entity = self._by_id.get(product_id)
        if entity is None or entity.merchant_id != merchant_id:
            return None  # tenant guard
        return entity

    def get_by_sku(self, merchant_id: str, sku: str) -> ProductEntity | None:
        product_id = self._sku_index.get((merchant_id, sku))
        if product_id is None:
            return None
        return self._by_id.get(product_id)

    def update(self, entity: ProductEntity) -> ProductEntity:
        existing = self._by_id.get(entity.id)
        if existing is None or existing.merchant_id != entity.merchant_id:
            raise ValueError("not found or tenant mismatch")
        # Remove old SKU index if changed
        old_sku_key = (existing.merchant_id, existing.sku)
        new_sku_key = (entity.merchant_id, entity.sku)
        if old_sku_key != new_sku_key:
            self._sku_index.pop(old_sku_key, None)
            self._sku_index[new_sku_key] = entity.id
        self._by_id[entity.id] = entity
        return entity

    def list_for_merchant(
        self, merchant_id: str, *, cursor: str | None = None, limit: int = 20
    ) -> list[ProductEntity]:
        results = [e for e in self._by_id.values() if e.merchant_id == merchant_id]
        results.sort(key=lambda p: (p.created_at, p.id))
        if cursor:
            results = [r for r in results if r.id > cursor]
        return results[:limit]

    def list_published(
        self, merchant_id: str, *, cursor: str | None = None, limit: int = 20
    ) -> list[ProductEntity]:
        return [
            p
            for p in self.list_for_merchant(merchant_id, cursor=cursor, limit=limit)
            if p.status is ProductStatus.PUBLISHED
        ]

    def sku_exists_for_merchant(self, merchant_id: str, sku: str) -> bool:
        return (merchant_id, sku) in self._sku_index


class FakeProductImageRepository:
    """In-memory fake satisfying ProductImageRepository Protocol."""

    def __init__(self) -> None:
        self._store: dict[str, ProductImageEntity] = {}

    def _tenant_guard(self, img: ProductImageEntity, merchant_id: str, product_id: str) -> bool:
        return img.merchant_id == merchant_id and img.product_id == product_id

    def add(self, entity: ProductImageEntity) -> ProductImageEntity:
        # Enforce (product_id, sort_order) uniqueness
        for existing in self._store.values():
            if (
                existing.product_id == entity.product_id
                and existing.sort_order == entity.sort_order
            ):
                raise ValueError("duplicate sort_order for product")
        self._store[entity.id] = entity
        return entity

    def get(self, merchant_id: str, product_id: str, image_id: str) -> ProductImageEntity | None:
        img = self._store.get(image_id)
        if img is None or not self._tenant_guard(img, merchant_id, product_id):
            return None
        return img

    def list_for_product(self, merchant_id: str, product_id: str) -> list[ProductImageEntity]:
        return sorted(
            [
                img
                for img in self._store.values()
                if self._tenant_guard(img, merchant_id, product_id)
            ],
            key=lambda i: i.sort_order,
        )

    def delete(self, merchant_id: str, product_id: str, image_id: str) -> None:
        img = self._store.get(image_id)
        if img is not None and self._tenant_guard(img, merchant_id, product_id):
            del self._store[image_id]

    def count_for_product(self, merchant_id: str, product_id: str) -> int:
        return len(self.list_for_product(merchant_id, product_id))


# ---------------------------------------------------------------------------
# MerchantRepository contract tests
# ---------------------------------------------------------------------------


class TestMerchantRepositoryContract:
    def test_add_and_get_by_id(self) -> None:
        repo = FakeMerchantRepository()
        cmd = CreateMerchantDomain(id="mer_x", name="Acme", idempotency_key="idem_1")
        entity = repo.add(cmd)
        assert entity.id == "mer_x"
        assert entity.name == "Acme"
        assert repo.get_by_id("mer_x") is not None

    def test_get_missing_returns_none(self) -> None:
        repo = FakeMerchantRepository()
        assert repo.get_by_id("mer_missing") is None

    def test_exists(self) -> None:
        repo = FakeMerchantRepository()
        cmd = CreateMerchantDomain(id="mer_y", name="Beta", idempotency_key="k")
        repo.add(cmd)
        assert repo.exists("mer_y") is True
        assert repo.exists("mer_z") is False

    def test_duplicate_id_raises(self) -> None:
        repo = FakeMerchantRepository()
        cmd = CreateMerchantDomain(id="mer_dup", name="Dup", idempotency_key="k")
        repo.add(cmd)
        with pytest.raises(ValueError):
            repo.add(cmd)


# ---------------------------------------------------------------------------
# MerchantUserRepository contract tests
# ---------------------------------------------------------------------------


class TestMerchantUserRepositoryContract:
    def test_add_membership(self) -> None:
        repo = FakeMerchantUserRepository()
        cmd = AddMerchantUserDomain(
            id="musr_1", merchant_id="mer_a", user_id="u_1", role=MerchantRole.ADMIN
        )
        entity = repo.add(cmd)
        assert entity.merchant_id == "mer_a"
        assert entity.user_id == "u_1"
        assert entity.role is MerchantRole.ADMIN

    def test_duplicate_membership_rejected(self) -> None:
        """Correctness 1: Merchant membership represented safely; unique constraint enforced."""
        repo = FakeMerchantUserRepository()
        cmd = AddMerchantUserDomain(
            id="musr_1", merchant_id="mer_a", user_id="u_1", role=MerchantRole.ADMIN
        )
        repo.add(cmd)
        cmd2 = AddMerchantUserDomain(
            id="musr_2", merchant_id="mer_a", user_id="u_1", role=MerchantRole.VIEWER
        )
        with pytest.raises(ValueError, match="duplicate"):
            repo.add(cmd2)

    def test_is_member_positive(self) -> None:
        repo = FakeMerchantUserRepository()
        cmd = AddMerchantUserDomain(
            id="musr_1", merchant_id="mer_a", user_id="u_1", role=MerchantRole.EDITOR
        )
        repo.add(cmd)
        assert repo.is_member("mer_a", "u_1") is True

    def test_is_member_negative(self) -> None:
        repo = FakeMerchantUserRepository()
        assert repo.is_member("mer_a", "u_ghost") is False

    def test_list_for_merchant_is_tenant_scoped(self) -> None:
        """Correctness 2: Merchant A and B membership lists are separate."""
        repo = FakeMerchantUserRepository()
        repo.add(AddMerchantUserDomain("m1", "mer_a", "u_1", MerchantRole.ADMIN))
        repo.add(AddMerchantUserDomain("m2", "mer_b", "u_2", MerchantRole.ADMIN))
        repo.add(AddMerchantUserDomain("m3", "mer_a", "u_3", MerchantRole.VIEWER))

        a_members = repo.list_for_merchant("mer_a")
        b_members = repo.list_for_merchant("mer_b")

        assert all(m.merchant_id == "mer_a" for m in a_members)
        assert all(m.merchant_id == "mer_b" for m in b_members)
        assert len(a_members) == 2
        assert len(b_members) == 1


# ---------------------------------------------------------------------------
# ProductRepository contract tests
# ---------------------------------------------------------------------------


class TestProductRepositoryContract:
    def test_add_and_get_by_id(self) -> None:
        repo = FakeProductRepository()
        p = _make_product(product_id="prod_1", merchant_id="mer_a")
        stored = repo.add(p)
        assert stored.id == "prod_1"
        assert repo.get_by_id("mer_a", "prod_1") is not None

    def test_get_by_id_tenant_guard(self) -> None:
        """Correctness 2: Merchant B cannot read Merchant A product."""
        repo = FakeProductRepository()
        repo.add(_make_product(product_id="prod_1", merchant_id="mer_a"))
        # Merchant B attempting to read mer_a product
        assert repo.get_by_id("mer_b", "prod_1") is None

    def test_duplicate_sku_same_merchant_rejected(self) -> None:
        """Correctness 3: Duplicate SKU within one merchant is rejected."""
        repo = FakeProductRepository()
        repo.add(_make_product("prod_1", "mer_a", "SKU-X"))
        with pytest.raises(ValueError, match="SKU"):
            repo.add(_make_product("prod_2", "mer_a", "SKU-X"))

    def test_same_sku_different_merchants_allowed(self) -> None:
        """Correctness 4: Same SKU for different merchants is allowed."""
        repo = FakeProductRepository()
        repo.add(_make_product("prod_a", "mer_a", "SKU-X"))
        repo.add(_make_product("prod_b", "mer_b", "SKU-X"))  # must not raise
        assert repo.get_by_sku("mer_a", "SKU-X") is not None
        assert repo.get_by_sku("mer_b", "SKU-X") is not None

    def test_integer_price_stored(self) -> None:
        """Correctness 5: Money stored as integer minor units."""
        p = _make_product()
        assert isinstance(p.price.amount_minor, int)

    def test_currency_explicit(self) -> None:
        """Correctness 6: Currency is explicit."""
        p = _make_product()
        assert p.price.currency == "INR"

    def test_version_persisted(self) -> None:
        """Correctness 7: Product version is persisted."""
        repo = FakeProductRepository()
        p = _make_product(version=5)
        stored = repo.add(p)
        assert stored.version == 5

    def test_publication_status_persisted(self) -> None:
        """Correctness 8: Publication status is persisted."""
        repo = FakeProductRepository()
        p = _make_product(status=ProductStatus.PUBLISHED)
        stored = repo.add(p)
        assert stored.status is ProductStatus.PUBLISHED

    def test_list_for_merchant_is_tenant_scoped(self) -> None:
        repo = FakeProductRepository()
        repo.add(_make_product("prod_a1", "mer_a", "SKU-1"))
        repo.add(_make_product("prod_a2", "mer_a", "SKU-2"))
        repo.add(_make_product("prod_b1", "mer_b", "SKU-1"))

        a_products = repo.list_for_merchant("mer_a")
        b_products = repo.list_for_merchant("mer_b")

        assert all(p.merchant_id == "mer_a" for p in a_products)
        assert all(p.merchant_id == "mer_b" for p in b_products)
        assert len(a_products) == 2
        assert len(b_products) == 1

    def test_list_published_excludes_drafts(self) -> None:
        repo = FakeProductRepository()
        repo.add(_make_product("p1", "mer_a", "SKU-1", ProductStatus.PUBLISHED))
        repo.add(_make_product("p2", "mer_a", "SKU-2", ProductStatus.DRAFT))
        repo.add(_make_product("p3", "mer_a", "SKU-3", ProductStatus.UNPUBLISHED))

        published = repo.list_published("mer_a")
        assert len(published) == 1
        assert published[0].id == "p1"

    def test_sku_exists_for_merchant(self) -> None:
        repo = FakeProductRepository()
        repo.add(_make_product("prod_1", "mer_a", "SKU-A"))
        assert repo.sku_exists_for_merchant("mer_a", "SKU-A") is True
        assert repo.sku_exists_for_merchant("mer_a", "SKU-B") is False
        assert repo.sku_exists_for_merchant("mer_b", "SKU-A") is False


# ---------------------------------------------------------------------------
# ProductImageRepository contract tests
# ---------------------------------------------------------------------------


class TestProductImageRepositoryContract:
    def test_add_and_get(self) -> None:
        repo = FakeProductImageRepository()
        img = _make_image("pimg_1", "mer_a", "prod_1", sort_order=0)
        stored = repo.add(img)
        assert stored.id == "pimg_1"
        result = repo.get("mer_a", "prod_1", "pimg_1")
        assert result is not None

    def test_get_tenant_guard_wrong_merchant(self) -> None:
        """Correctness 10: Image ownership cannot escape merchant boundary."""
        repo = FakeProductImageRepository()
        repo.add(_make_image("pimg_1", "mer_a", "prod_1"))
        assert repo.get("mer_b", "prod_1", "pimg_1") is None

    def test_get_tenant_guard_wrong_product(self) -> None:
        """Correctness 10: Image ownership cannot escape product boundary."""
        repo = FakeProductImageRepository()
        repo.add(_make_image("pimg_1", "mer_a", "prod_1"))
        assert repo.get("mer_a", "prod_2", "pimg_1") is None

    def test_duplicate_sort_order_rejected(self) -> None:
        repo = FakeProductImageRepository()
        repo.add(_make_image("pimg_1", "mer_a", "prod_1", sort_order=0))
        with pytest.raises(ValueError, match="sort_order"):
            repo.add(_make_image("pimg_2", "mer_a", "prod_1", sort_order=0))

    def test_list_for_product_sorted_by_sort_order(self) -> None:
        repo = FakeProductImageRepository()
        repo.add(_make_image("pimg_2", sort_order=1))
        repo.add(_make_image("pimg_0", sort_order=0))
        images = repo.list_for_product("mer_a", "prod_1")
        assert [i.sort_order for i in images] == [0, 1]

    def test_count_for_product(self) -> None:
        repo = FakeProductImageRepository()
        repo.add(_make_image("pimg_0", sort_order=0))
        repo.add(_make_image("pimg_1", sort_order=1))
        assert repo.count_for_product("mer_a", "prod_1") == 2

    def test_delete_image(self) -> None:
        repo = FakeProductImageRepository()
        repo.add(_make_image("pimg_1"))
        repo.delete("mer_a", "prod_1", "pimg_1")
        assert repo.get("mer_a", "prod_1", "pimg_1") is None

    def test_delete_wrong_merchant_is_noop(self) -> None:
        """Delete with wrong merchant_id must not delete the image."""
        repo = FakeProductImageRepository()
        repo.add(_make_image("pimg_1", "mer_a", "prod_1"))
        repo.delete("mer_b", "prod_1", "pimg_1")  # wrong tenant
        # Image must still be there for the real merchant
        assert repo.get("mer_a", "prod_1", "pimg_1") is not None
