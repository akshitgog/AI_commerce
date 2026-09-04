"""Product, ProductMetadata, and ProductImage domain entities.

Pure-Python frozen dataclasses; no ORM state.  All commercial fields
(price_minor, currency, available_quantity, status, version) are
authoritative merchant-controlled data.  AI-enriched descriptive data
lives in ProductMetadataEntity and is strictly separate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ai_commerce_gateway.domain.enums import ProductStatus, ReviewStatus

# ---------------------------------------------------------------------------
# Money value object
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MoneyMinor:
    """Canonical representation of an amount: integer minor units + ISO-4217 currency."""

    amount_minor: int  # e.g. 10000 == ₹100.00
    currency: str  # 3-character ISO code, e.g. "INR"

    def __post_init__(self) -> None:
        if self.amount_minor < 0:
            raise ValueError("amount_minor must be >= 0")
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError(f"currency must be a 3-letter ISO code, got {self.currency!r}")


# ---------------------------------------------------------------------------
# ProductImage
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProductImageEntity:
    """Read-only snapshot of a ProductImage record.

    Ownership is enforced by the pair (product_id, merchant_id) so that
    an image can never escape its product/merchant relationship.
    """

    id: str
    merchant_id: str  # retained for direct tenant-scoped access patterns
    product_id: str
    storage_path: str
    public_url: str | None
    alt_text: str | None
    sort_order: int  # 0-based, 0–2 per product
    created_at: datetime

    def __post_init__(self) -> None:
        if self.sort_order < 0:
            raise ValueError("sort_order must be >= 0")

    def belongs_to(self, merchant_id: str, product_id: str) -> bool:
        """Return True iff this image belongs to the given merchant+product."""
        return self.merchant_id == merchant_id and self.product_id == product_id


# ---------------------------------------------------------------------------
# ProductMetadata — AI enrichment, strictly non-authoritative
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProductMetadataEntity:
    """Descriptive AI-enrichment metadata; never touches price, stock, or status.

    This entity is deliberately separate from ProductEntity so that there
    is no accidental path from AI-enriched content to commercial fields.
    """

    product_id: str
    tags: tuple[str, ...]
    attributes: dict[str, object]
    search_text: str | None
    source: str  # "MERCHANT" | "AI"
    review_status: ReviewStatus
    updated_at: datetime


# ---------------------------------------------------------------------------
# Product — authoritative commercial record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProductEntity:
    """Read-only snapshot of a Product record.

    Commercial fields (price_minor, currency, available_quantity, status,
    version) are authoritative merchant-owned data.  AI enrichment is held
    in a separate ProductMetadataEntity and must never overwrite these fields.
    """

    id: str
    merchant_id: str
    sku: str
    title: str
    description: str
    category: str | None
    # ---- authoritative commercial fields ----
    price: MoneyMinor   # integer minor units + explicit currency
    available_quantity: int  # >= 0
    status: ProductStatus
    version: int  # >= 1, incremented on every write
    # -----------------------------------------
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.available_quantity < 0:
            raise ValueError("available_quantity must be >= 0")
        if self.version < 1:
            raise ValueError("version must be >= 1")

    def is_published(self) -> bool:
        return self.status is ProductStatus.PUBLISHED

    def belongs_to(self, merchant_id: str) -> bool:
        return self.merchant_id == merchant_id
