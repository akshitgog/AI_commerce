"""Repository abstractions for the Merchant/Catalog domain.

These Protocol definitions are the boundary between the application layer
and the persistence layer.  Any SQLAlchemy implementation must satisfy
these interfaces so that tests may substitute in-memory fakes.

All repositories are tenant-scoped: every query or mutation that touches
data owned by a merchant MUST receive a ``merchant_id`` and filter by it.
Cross-tenant access is structurally impossible through these interfaces.
"""

from __future__ import annotations

from typing import Protocol

from ai_commerce_gateway.domain.idempotency import CatalogIdempotencyRecord
from ai_commerce_gateway.domain.merchant import (
    AddMerchantUserDomain,
    CreateMerchantDomain,
    MerchantEntity,
    MerchantUserEntity,
)
from ai_commerce_gateway.domain.policy import MerchantPolicyEntity
from ai_commerce_gateway.domain.product import (
    ProductEntity,
    ProductImageEntity,
    ProductMetadataEntity,
)


class MerchantRepository(Protocol):
    """Persistence operations for Merchant aggregates."""

    def add(self, domain: CreateMerchantDomain) -> MerchantEntity:
        """Persist a new Merchant and return its entity snapshot."""
        ...

    def get_by_id(self, merchant_id: str) -> MerchantEntity | None:
        """Return the Merchant or None if not found."""
        ...

    def exists(self, merchant_id: str) -> bool:
        """Return True iff the Merchant exists (any status)."""
        ...


class MerchantUserRepository(Protocol):
    """Persistence operations for merchant membership."""

    def add(self, domain: AddMerchantUserDomain) -> MerchantUserEntity:
        """Persist a MerchantUser and return its entity snapshot.

        The backing store enforces (merchant_id, user_id) uniqueness.
        """
        ...

    def get(self, merchant_id: str, user_id: str) -> MerchantUserEntity | None:
        """Return the membership or None."""
        ...

    def list_for_merchant(self, merchant_id: str) -> list[MerchantUserEntity]:
        """Return all members of the merchant, ordered by created_at."""
        ...

    def is_member(self, merchant_id: str, user_id: str) -> bool:
        """Return True iff the user is a member of the merchant."""
        ...


class ProductRepository(Protocol):
    """Tenant-scoped persistence for Product records.

    Every write increments version atomically.  Every query scopes by
    merchant_id so cross-tenant access is structurally prevented.
    """

    def add(self, entity: ProductEntity) -> ProductEntity:
        """Persist a new Product and return the stored snapshot."""
        ...

    def get_by_id(self, merchant_id: str, product_id: str) -> ProductEntity | None:
        """Return the Product or None; scoped to merchant_id."""
        ...

    def get_by_sku(self, merchant_id: str, sku: str) -> ProductEntity | None:
        """Return the Product with the given SKU or None; merchant-scoped."""
        ...

    def update(self, entity: ProductEntity) -> ProductEntity:
        """Persist updated product state (version must already be incremented)."""
        ...

    def list_for_merchant(
        self,
        merchant_id: str,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> list[ProductEntity]:
        """Return products for the merchant, ordered by created_at."""
        ...

    def list_published(
        self,
        merchant_id: str,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> list[ProductEntity]:
        """Return only PUBLISHED products for buyer discovery."""
        ...

    def sku_exists_for_merchant(self, merchant_id: str, sku: str) -> bool:
        """Return True iff the SKU already exists for this merchant."""
        ...


class ProductMetadataRepository(Protocol):
    """Persistence for ProductMetadata — always subordinate to the product."""

    def get(self, merchant_id: str, product_id: str) -> ProductMetadataEntity | None:
        """Return the metadata for a product, or None if not yet created."""
        ...

    def upsert(self, merchant_id: str, entity: ProductMetadataEntity) -> ProductMetadataEntity:
        """Create or replace the metadata for the product.

        This operation MUST NOT allow changes to price, currency, stock or
        publication status.  Those fields live in Product, not ProductMetadata.
        """
        ...


class ProductImageRepository(Protocol):
    """Tenant + product-scoped persistence for ProductImage records."""

    def add(self, entity: ProductImageEntity) -> ProductImageEntity:
        """Persist a ProductImage.

        The backing store enforces (product_id, sort_order) uniqueness and
        (storage_path) uniqueness.
        """
        ...

    def get(self, merchant_id: str, product_id: str, image_id: str) -> ProductImageEntity | None:
        """Return the image or None; scoped to both merchant and product."""
        ...

    def list_for_product(
        self,
        merchant_id: str,
        product_id: str,
    ) -> list[ProductImageEntity]:
        """Return images in sort_order ascending; merchant+product scoped."""
        ...

    def delete(self, merchant_id: str, product_id: str, image_id: str) -> None:
        """Delete the image; scoped to merchant+product to prevent escapes."""
        ...

    def count_for_product(self, merchant_id: str, product_id: str) -> int:
        """Return the current image count; V1 max is 3."""
        ...


class MerchantPolicyRepository(Protocol):
    """Persistence for MerchantPolicy; data/foundation only (evaluation is B2)."""

    def get_active(self, merchant_id: str) -> MerchantPolicyEntity | None:
        """Return the currently ACTIVE policy for the merchant, or None."""
        ...

    def add(self, entity: MerchantPolicyEntity) -> MerchantPolicyEntity:
        """Persist a new policy version."""
        ...

    def update(self, entity: MerchantPolicyEntity) -> MerchantPolicyEntity:
        """Persist an updated policy; version already incremented by caller."""
        ...


class IdempotencyRepository(Protocol):
    """Persistence for catalog-mutation idempotency records.

    Uses the shared ``idempotency_records`` table.  The unique constraint
    on ``(actor_id, operation, idempotency_key)`` ensures at-most-once
    execution per caller+operation+key triple.
    """

    def get(
        self, *, actor_id: str, operation: str, idempotency_key: str
    ) -> CatalogIdempotencyRecord | None:
        """Return the existing record or None."""
        ...

    def claim(
        self, record: CatalogIdempotencyRecord
    ) -> tuple[CatalogIdempotencyRecord, bool]:
        """Attempt to atomically claim the idempotency slot.

        Returns ``(record, True)`` if this call inserted the record, or
        ``(existing_record, False)`` if a record already existed for the
        same ``(actor_id, operation, idempotency_key)``.
        """
        ...

    def save_result(
        self,
        record_id: str,
        *,
        resource_type: str,
        resource_id: str,
        response_code: int,
        response_body_hash: str,
    ) -> None:
        """Persist the outcome of a successfully executed operation."""
        ...
