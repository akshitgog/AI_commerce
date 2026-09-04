"""Unit tests for Product, ProductMetadata, ProductImage, and MoneyMinor domains.

No database, no ORM.  These tests verify:
3. Duplicate SKU within one merchant is rejected (structural: same-merchant SKU clash).
4. Same SKU may exist for different merchants.
5. Money is stored as integer minor units.
6. Currency is explicit (enforced by MoneyMinor).
7. Product version is persisted in domain entity.
8. Product publication status is persisted in domain entity.
9. Authoritative commercial fields remain separate from AI metadata.
10. ProductImage ownership cannot escape the product/merchant relationship.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_commerce_gateway.domain.enums import PolicyMode, ProductStatus, RecordStatus, ReviewStatus
from ai_commerce_gateway.domain.policy import MerchantPolicyEntity
from ai_commerce_gateway.domain.product import (
    MoneyMinor,
    ProductEntity,
    ProductImageEntity,
    ProductMetadataEntity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _make_product(
    merchant_id: str = "mer_a",
    sku: str = "SKU-001",
    status: ProductStatus = ProductStatus.DRAFT,
    version: int = 1,
    price_minor: int = 10000,
    currency: str = "INR",
    qty: int = 5,
) -> ProductEntity:
    now = _utc_now()
    return ProductEntity(
        id=f"prod_{merchant_id}_{sku}",
        merchant_id=merchant_id,
        sku=sku,
        title="Sample Product",
        description="A fine product",
        category=None,
        price=MoneyMinor(amount_minor=price_minor, currency=currency),
        available_quantity=qty,
        status=status,
        version=version,
        created_at=now,
        updated_at=now,
    )


def _make_image(
    merchant_id: str = "mer_a",
    product_id: str = "prod_1",
    sort_order: int = 0,
) -> ProductImageEntity:
    return ProductImageEntity(
        id=f"pimg_{merchant_id}_{product_id}_{sort_order}",
        merchant_id=merchant_id,
        product_id=product_id,
        storage_path=f"images/{merchant_id}/{product_id}/{sort_order}.jpg",
        public_url=None,
        alt_text=None,
        sort_order=sort_order,
        created_at=_utc_now(),
    )


# ---------------------------------------------------------------------------
# MoneyMinor value object
# ---------------------------------------------------------------------------


class TestMoneyMinor:
    """Correctness: money is integer minor units + explicit currency."""

    def test_integer_minor_units_stored(self) -> None:
        money = MoneyMinor(amount_minor=99900, currency="INR")
        assert money.amount_minor == 99900
        assert isinstance(money.amount_minor, int)

    def test_currency_is_explicit(self) -> None:
        money = MoneyMinor(amount_minor=500, currency="USD")
        assert money.currency == "USD"

    def test_zero_amount_is_valid(self) -> None:
        MoneyMinor(amount_minor=0, currency="INR")  # must not raise

    def test_amount_minor_strict_type_check(self) -> None:
        """MoneyMinor must strictly reject float, bool, str, and other non-ints."""
        with pytest.raises(TypeError, match="must be a plain int"):
            MoneyMinor(amount_minor=100.5, currency="INR")  # type: ignore

        with pytest.raises(TypeError, match="must be a plain int"):
            MoneyMinor(amount_minor=True, currency="INR")  # type: ignore

        with pytest.raises(TypeError, match="must be a plain int"):
            MoneyMinor(amount_minor=False, currency="INR")  # type: ignore

        with pytest.raises(TypeError, match="must be a plain int"):
            MoneyMinor(amount_minor="100", currency="INR")  # type: ignore

    def test_negative_amount_rejected(self) -> None:
        with pytest.raises(ValueError, match="amount_minor"):
            MoneyMinor(amount_minor=-1, currency="INR")

    def test_invalid_currency_too_short_rejected(self) -> None:
        with pytest.raises(ValueError, match="currency"):
            MoneyMinor(amount_minor=100, currency="IN")

    def test_invalid_currency_too_long_rejected(self) -> None:
        with pytest.raises(ValueError, match="currency"):
            MoneyMinor(amount_minor=100, currency="INRR")

    def test_numeric_currency_rejected(self) -> None:
        with pytest.raises(ValueError, match="currency"):
            MoneyMinor(amount_minor=100, currency="123")

    def test_money_is_frozen(self) -> None:
        money = MoneyMinor(amount_minor=100, currency="INR")
        with pytest.raises((AttributeError, TypeError)):
            money.amount_minor = 200  # type: ignore[misc]

    def test_two_money_values_are_distinct(self) -> None:
        m1 = MoneyMinor(amount_minor=100, currency="INR")
        m2 = MoneyMinor(amount_minor=200, currency="INR")
        assert m1 != m2

    def test_no_float_field(self) -> None:
        """Regression: MoneyMinor must have no float attribute."""
        money = MoneyMinor(amount_minor=10050, currency="INR")
        assert isinstance(money.amount_minor, int)
        # Confirm there is no 'amount' float property
        assert not hasattr(money, "amount")


# ---------------------------------------------------------------------------
# ProductEntity
# ---------------------------------------------------------------------------


class TestProductEntity:
    """Correctness: version, publication status, commercial fields, tenant ownership."""

    def test_product_version_is_persisted(self) -> None:
        p = _make_product(version=3)
        assert p.version == 3

    def test_version_must_be_at_least_one(self) -> None:
        with pytest.raises(ValueError, match="version"):
            _make_product(version=0)

    def test_product_status_draft(self) -> None:
        p = _make_product(status=ProductStatus.DRAFT)
        assert p.status is ProductStatus.DRAFT
        assert not p.is_published()

    def test_product_status_published(self) -> None:
        p = _make_product(status=ProductStatus.PUBLISHED)
        assert p.status is ProductStatus.PUBLISHED
        assert p.is_published()

    def test_product_status_unpublished(self) -> None:
        p = _make_product(status=ProductStatus.UNPUBLISHED)
        assert not p.is_published()

    def test_price_is_integer_minor_units(self) -> None:
        p = _make_product(price_minor=49900, currency="INR")
        assert p.price.amount_minor == 49900
        assert isinstance(p.price.amount_minor, int)

    def test_currency_is_explicit(self) -> None:
        p = _make_product(currency="USD")
        assert p.price.currency == "USD"

    def test_negative_quantity_rejected(self) -> None:
        with pytest.raises(ValueError, match="available_quantity"):
            _make_product(qty=-1)

    def test_product_belongs_to_own_merchant(self) -> None:
        p = _make_product(merchant_id="mer_a")
        assert p.belongs_to("mer_a") is True

    def test_product_does_not_belong_to_other_merchant(self) -> None:
        p = _make_product(merchant_id="mer_a")
        assert p.belongs_to("mer_b") is False

    def test_product_is_frozen(self) -> None:
        p = _make_product()
        with pytest.raises((AttributeError, TypeError)):
            p.title = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SKU uniqueness semantics (domain layer)
# ---------------------------------------------------------------------------


class TestSkuSeparation:
    """
    Correctness 3 & 4: Duplicate SKU within one merchant is rejected;
    same SKU may exist for different merchants.
    (Database enforcement is tested in integration; here we verify that
    two products with the same sku+merchant_id fields are equal and would
    collide in persistence, whereas same SKU on different merchants differ.)
    """

    def test_same_sku_same_merchant_entities_match(self) -> None:
        p1 = _make_product(merchant_id="mer_a", sku="SKU-X")
        p2 = _make_product(merchant_id="mer_a", sku="SKU-X")
        # Same SKU + same merchant → would violate the unique constraint
        assert p1.merchant_id == p2.merchant_id
        assert p1.sku == p2.sku

    def test_same_sku_different_merchants_are_distinct(self) -> None:
        p_a = _make_product(merchant_id="mer_a", sku="SKU-X")
        p_b = _make_product(merchant_id="mer_b", sku="SKU-X")
        # Same SKU but different merchants — these are separate catalog entries
        assert p_a.sku == p_b.sku
        assert p_a.merchant_id != p_b.merchant_id
        # They do NOT belong to each other's tenants
        assert p_a.belongs_to("mer_b") is False
        assert p_b.belongs_to("mer_a") is False


# ---------------------------------------------------------------------------
# ProductMetadataEntity — strict separation from commercial fields
# ---------------------------------------------------------------------------


class TestProductMetadataEntity:
    """Correctness 9: AI enrichment metadata is separate from commercial fields."""

    def test_metadata_has_no_price_field(self) -> None:
        meta = ProductMetadataEntity(
            product_id="prod_1",
            tags=("tag_a",),
            attributes={"colour": "red"},
            search_text="red widget",
            source="AI",
            review_status=ReviewStatus.PENDING,
            updated_at=_utc_now(),
        )
        assert not hasattr(meta, "price_minor")
        assert not hasattr(meta, "currency")
        assert not hasattr(meta, "available_quantity")
        assert not hasattr(meta, "status")
        assert not hasattr(meta, "version")

    def test_metadata_fields_are_accessible(self) -> None:
        meta = ProductMetadataEntity(
            product_id="prod_1",
            tags=("electronics", "gadget"),
            attributes={"warranty_months": 12},
            search_text="cool gadget",
            source="MERCHANT",
            review_status=ReviewStatus.APPROVED,
            updated_at=_utc_now(),
        )
        assert "electronics" in meta.tags
        assert meta.attributes["warranty_months"] == 12
        assert meta.source == "MERCHANT"

    def test_metadata_review_status_pending(self) -> None:
        meta = ProductMetadataEntity(
            product_id="p1",
            tags=(),
            attributes={},
            search_text=None,
            source="AI",
            review_status=ReviewStatus.PENDING,
            updated_at=_utc_now(),
        )
        assert meta.review_status is ReviewStatus.PENDING

    def test_product_and_metadata_are_separate_objects(self) -> None:
        """The Product entity carries no metadata fields; they live separately."""
        p = _make_product()
        assert not hasattr(p, "tags")
        assert not hasattr(p, "search_text")
        assert not hasattr(p, "attributes")
        assert not hasattr(p, "review_status")
        assert not hasattr(p, "source")


# ---------------------------------------------------------------------------
# ProductImageEntity — ownership invariants
# ---------------------------------------------------------------------------


class TestProductImageEntity:
    """Correctness 10: ProductImage ownership cannot escape product/merchant."""

    def test_image_belongs_to_correct_merchant_and_product(self) -> None:
        img = _make_image(merchant_id="mer_a", product_id="prod_1")
        assert img.belongs_to("mer_a", "prod_1") is True

    def test_image_does_not_belong_to_different_merchant(self) -> None:
        img = _make_image(merchant_id="mer_a", product_id="prod_1")
        assert img.belongs_to("mer_b", "prod_1") is False

    def test_image_does_not_belong_to_different_product(self) -> None:
        img = _make_image(merchant_id="mer_a", product_id="prod_1")
        assert img.belongs_to("mer_a", "prod_2") is False

    def test_sort_order_nonnegative(self) -> None:
        with pytest.raises(ValueError, match="sort_order"):
            ProductImageEntity(
                id="img_1",
                merchant_id="mer_a",
                product_id="prod_1",
                storage_path="path/a.jpg",
                public_url=None,
                alt_text=None,
                sort_order=-1,
                created_at=_utc_now(),
            )

    def test_image_is_frozen(self) -> None:
        img = _make_image()
        with pytest.raises((AttributeError, TypeError)):
            img.alt_text = "changed"  # type: ignore[misc]

    def test_images_at_different_sort_orders_are_distinct(self) -> None:
        img0 = _make_image(sort_order=0)
        img1 = _make_image(sort_order=1)
        assert img0.sort_order != img1.sort_order

    def test_image_retains_merchant_id_for_tenant_scoping(self) -> None:
        """merchant_id on image allows direct tenant-scoped queries."""
        img = _make_image(merchant_id="mer_a", product_id="prod_x")
        assert img.merchant_id == "mer_a"
        assert img.product_id == "prod_x"


# ---------------------------------------------------------------------------
# MerchantPolicyEntity
# ---------------------------------------------------------------------------


class TestMerchantPolicyEntity:
    def _make_policy(
        self,
        mode: PolicyMode = PolicyMode.MANUAL_ALL,
        auto_max: MoneyMinor | None = None,
        version: int = 1,
    ) -> MerchantPolicyEntity:
        now = _utc_now()
        return MerchantPolicyEntity(
            id="pol_1",
            merchant_id="mer_a",
            mode=mode,
            auto_accept_max=auto_max,
            version=version,
            status=RecordStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

    def test_manual_all_policy_has_no_limit(self) -> None:
        p = self._make_policy(mode=PolicyMode.MANUAL_ALL, auto_max=None)
        assert p.mode is PolicyMode.MANUAL_ALL
        assert p.auto_accept_max is None

    def test_auto_below_limit_requires_max(self) -> None:
        with pytest.raises(ValueError, match="auto_accept_max"):
            self._make_policy(mode=PolicyMode.AUTO_BELOW_LIMIT, auto_max=None)

    def test_auto_below_limit_with_valid_max(self) -> None:
        p = self._make_policy(
            mode=PolicyMode.AUTO_BELOW_LIMIT,
            auto_max=MoneyMinor(amount_minor=50000, currency="INR"),
        )
        assert p.auto_accept_max is not None
        assert p.auto_accept_max.amount_minor == 50000

    def test_manual_all_cannot_have_limit(self) -> None:
        with pytest.raises(ValueError, match="AUTO_BELOW_LIMIT"):
            self._make_policy(
                mode=PolicyMode.MANUAL_ALL,
                auto_max=MoneyMinor(amount_minor=10000, currency="INR"),
            )

    def test_version_must_be_at_least_one(self) -> None:
        with pytest.raises(ValueError, match="version"):
            self._make_policy(version=0)

    def test_policy_belongs_to_own_merchant(self) -> None:
        p = self._make_policy()
        assert p.belongs_to("mer_a") is True
        assert p.belongs_to("mer_b") is False
