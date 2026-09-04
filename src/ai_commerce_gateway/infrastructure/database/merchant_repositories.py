"""SQLAlchemy repository implementations for the Merchant/Catalog domain.

These implementations satisfy the Protocol definitions in
``ai_commerce_gateway.domain.repositories`` using the ORM models from
``ai_commerce_gateway.infrastructure.database.models``.

All queries are tenant-scoped: every SELECT on merchant-owned data filters
by ``merchant_id``.  Uniqueness constraints are enforced by the database
(not application code) so concurrent inserts are safe.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import (
    MerchantRole,
    PolicyMode,
    ProductStatus,
    RecordStatus,
    ReviewStatus,
)
from ai_commerce_gateway.domain.merchant import (
    AddMerchantUserDomain,
    CreateMerchantDomain,
    MerchantEntity,
    MerchantUserEntity,
)
from ai_commerce_gateway.domain.policy import MerchantPolicyEntity
from ai_commerce_gateway.domain.product import (
    MoneyMinor,
    ProductEntity,
    ProductImageEntity,
    ProductMetadataEntity,
)
from ai_commerce_gateway.infrastructure.database import models as orm

# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _orm_merchant_to_entity(row: orm.Merchant) -> MerchantEntity:
    return MerchantEntity(
        id=row.id,
        name=row.name,
        status=RecordStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _orm_merchant_user_to_entity(row: orm.MerchantUser) -> MerchantUserEntity:
    return MerchantUserEntity(
        id=row.id,
        merchant_id=row.merchant_id,
        user_id=row.user_id,
        role=MerchantRole(row.role),
        created_at=row.created_at,
    )


def _orm_product_to_entity(row: orm.Product) -> ProductEntity:
    return ProductEntity(
        id=row.id,
        merchant_id=row.merchant_id,
        sku=row.sku,
        title=row.title,
        description=row.description,
        category=row.category,
        price=MoneyMinor(amount_minor=row.price_minor, currency=row.currency),
        available_quantity=row.available_quantity,
        status=ProductStatus(row.status),
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _orm_product_image_to_entity(row: orm.ProductImage) -> ProductImageEntity:
    return ProductImageEntity(
        id=row.id,
        merchant_id=row.merchant_id,
        product_id=row.product_id,
        storage_path=row.storage_path,
        public_url=row.public_url,
        alt_text=row.alt_text,
        sort_order=row.sort_order,
        created_at=row.created_at,
    )


def _orm_product_metadata_to_entity(row: orm.ProductMetadata) -> ProductMetadataEntity:
    tags_raw = row.tags
    tags: tuple[str, ...] = tuple(tags_raw) if isinstance(tags_raw, list) else ()
    attrs_raw = row.attributes_json
    attrs: dict[str, object] = dict(attrs_raw) if isinstance(attrs_raw, dict) else {}
    return ProductMetadataEntity(
        product_id=row.product_id,
        tags=tags,
        attributes=attrs,
        search_text=row.search_text,
        source=row.source,
        review_status=ReviewStatus(row.review_status),
        updated_at=row.updated_at,
    )


def _orm_policy_to_entity(row: orm.MerchantPolicy) -> MerchantPolicyEntity:
    auto_accept: MoneyMinor | None = None
    if row.auto_accept_max_minor is not None and row.currency is not None:
        auto_accept = MoneyMinor(amount_minor=row.auto_accept_max_minor, currency=row.currency)
    return MerchantPolicyEntity(
        id=row.id,
        merchant_id=row.merchant_id,
        mode=PolicyMode(row.mode),
        auto_accept_max=auto_accept,
        version=row.version,
        status=RecordStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ---------------------------------------------------------------------------
# Merchant repository
# ---------------------------------------------------------------------------


class SqlAlchemyMerchantRepository:
    """SQLAlchemy implementation of MerchantRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, domain: CreateMerchantDomain) -> MerchantEntity:
        now = _now_utc()
        row = orm.Merchant(
            id=domain.id,
            name=domain.name,
            status=domain.status.value,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "Merchant with this ID already exists.",
                status_code=409,
            ) from exc
        return _orm_merchant_to_entity(row)

    def get_by_id(self, merchant_id: str) -> MerchantEntity | None:
        row = self._session.get(orm.Merchant, merchant_id)
        return _orm_merchant_to_entity(row) if row is not None else None

    def exists(self, merchant_id: str) -> bool:
        return self._session.get(orm.Merchant, merchant_id) is not None


# ---------------------------------------------------------------------------
# MerchantUser repository
# ---------------------------------------------------------------------------


class SqlAlchemyMerchantUserRepository:
    """SQLAlchemy implementation of MerchantUserRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, domain: AddMerchantUserDomain) -> MerchantUserEntity:
        now = _now_utc()
        row = orm.MerchantUser(
            id=domain.id,
            merchant_id=domain.merchant_id,
            user_id=domain.user_id,
            role=domain.role.value,
            created_at=now,
        )
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "User is already a member of this merchant.",
                status_code=409,
            ) from exc
        return _orm_merchant_user_to_entity(row)

    def get(self, merchant_id: str, user_id: str) -> MerchantUserEntity | None:
        stmt = select(orm.MerchantUser).where(
            orm.MerchantUser.merchant_id == merchant_id,
            orm.MerchantUser.user_id == user_id,
        )
        row = self._session.scalars(stmt).first()
        return _orm_merchant_user_to_entity(row) if row is not None else None

    def list_for_merchant(self, merchant_id: str) -> list[MerchantUserEntity]:
        stmt = (
            select(orm.MerchantUser)
            .where(orm.MerchantUser.merchant_id == merchant_id)
            .order_by(orm.MerchantUser.created_at)
        )
        return [_orm_merchant_user_to_entity(r) for r in self._session.scalars(stmt)]

    def is_member(self, merchant_id: str, user_id: str) -> bool:
        return self.get(merchant_id, user_id) is not None


# ---------------------------------------------------------------------------
# Product repository
# ---------------------------------------------------------------------------


class SqlAlchemyProductRepository:
    """SQLAlchemy implementation of ProductRepository.

    All queries filter on merchant_id to enforce tenant isolation at the
    query level (not just application level).
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: ProductEntity) -> ProductEntity:
        row = orm.Product(
            id=entity.id,
            merchant_id=entity.merchant_id,
            sku=entity.sku,
            title=entity.title,
            description=entity.description,
            category=entity.category,
            price_minor=entity.price.amount_minor,
            currency=entity.price.currency,
            available_quantity=entity.available_quantity,
            status=entity.status.value,
            version=entity.version,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                f"Product with SKU {entity.sku!r} already exists for this merchant.",
                status_code=409,
                details={"sku": entity.sku, "merchant_id": entity.merchant_id},
            ) from exc
        return _orm_product_to_entity(row)

    def get_by_id(self, merchant_id: str, product_id: str) -> ProductEntity | None:
        stmt = select(orm.Product).where(
            orm.Product.id == product_id,
            orm.Product.merchant_id == merchant_id,  # tenant guard
        )
        row = self._session.scalars(stmt).first()
        return _orm_product_to_entity(row) if row is not None else None

    def get_by_id_unscoped(self, product_id: str) -> ProductEntity | None:
        row = self._session.get(orm.Product, product_id)
        return _orm_product_to_entity(row) if row is not None else None


    def get_by_sku(self, merchant_id: str, sku: str) -> ProductEntity | None:
        stmt = select(orm.Product).where(
            orm.Product.merchant_id == merchant_id,
            orm.Product.sku == sku,
        )
        row = self._session.scalars(stmt).first()
        return _orm_product_to_entity(row) if row is not None else None

    def update(self, entity: ProductEntity) -> ProductEntity:
        stmt = select(orm.Product).where(
            orm.Product.id == entity.id,
            orm.Product.merchant_id == entity.merchant_id,  # tenant guard
        )
        row = self._session.scalars(stmt).first()
        if row is None:
            raise AppError(
                ErrorCode.NOT_FOUND,
                "Product not found or does not belong to this merchant.",
                status_code=404,
            )
        row.sku = entity.sku
        row.title = entity.title
        row.description = entity.description
        row.category = entity.category
        row.price_minor = entity.price.amount_minor
        row.currency = entity.price.currency
        row.available_quantity = entity.available_quantity
        row.status = entity.status.value
        row.version = entity.version
        row.updated_at = entity.updated_at
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                f"Product with SKU {entity.sku!r} already exists for this merchant.",
                status_code=409,
                details={"sku": entity.sku, "merchant_id": entity.merchant_id},
            ) from exc
        return _orm_product_to_entity(row)

    def list_for_merchant(
        self,
        merchant_id: str,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> list[ProductEntity]:
        stmt = (
            select(orm.Product)
            .where(orm.Product.merchant_id == merchant_id)
            .order_by(orm.Product.created_at, orm.Product.id)
            .limit(limit)
        )
        if cursor is not None:
            stmt = stmt.where(orm.Product.id > cursor)
        return [_orm_product_to_entity(r) for r in self._session.scalars(stmt)]

    def list_published(
        self,
        merchant_id: str,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> list[ProductEntity]:
        stmt = (
            select(orm.Product)
            .where(
                orm.Product.merchant_id == merchant_id,
                orm.Product.status == ProductStatus.PUBLISHED.value,
            )
            .order_by(orm.Product.created_at, orm.Product.id)
            .limit(limit)
        )
        if cursor is not None:
            stmt = stmt.where(orm.Product.id > cursor)
        return [_orm_product_to_entity(r) for r in self._session.scalars(stmt)]

    def sku_exists_for_merchant(self, merchant_id: str, sku: str) -> bool:
        return self.get_by_sku(merchant_id, sku) is not None


# ---------------------------------------------------------------------------
# ProductMetadata repository
# ---------------------------------------------------------------------------


class SqlAlchemyProductMetadataRepository:
    """SQLAlchemy implementation of ProductMetadataRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _verify_ownership(self, merchant_id: str, product_id: str) -> None:
        stmt = select(orm.Product.id).where(
            orm.Product.id == product_id,
            orm.Product.merchant_id == merchant_id,
        )
        if self._session.scalars(stmt).first() is None:
            raise AppError(
                ErrorCode.NOT_FOUND,
                "Product not found or does not belong to this merchant.",
                status_code=404,
            )

    def get(self, merchant_id: str, product_id: str) -> ProductMetadataEntity | None:
        self._verify_ownership(merchant_id, product_id)
        row = self._session.get(orm.ProductMetadata, product_id)
        return _orm_product_metadata_to_entity(row) if row is not None else None

    def upsert(self, merchant_id: str, entity: ProductMetadataEntity) -> ProductMetadataEntity:
        self._verify_ownership(merchant_id, entity.product_id)
        now = _now_utc()
        row = self._session.get(orm.ProductMetadata, entity.product_id)
        if row is None:
            row = orm.ProductMetadata(
                product_id=entity.product_id,
                tags=list(entity.tags),
                attributes_json=dict(entity.attributes),
                search_text=entity.search_text,
                source=entity.source,
                review_status=entity.review_status.value,
                updated_at=now,
            )
            self._session.add(row)
        else:
            row.tags = list(entity.tags)
            row.attributes_json = dict(entity.attributes)
            row.search_text = entity.search_text
            row.source = entity.source
            row.review_status = entity.review_status.value
            row.updated_at = now
        self._session.flush()
        return _orm_product_metadata_to_entity(row)


# ---------------------------------------------------------------------------
# ProductImage repository
# ---------------------------------------------------------------------------


class SqlAlchemyProductImageRepository:
    """SQLAlchemy implementation of ProductImageRepository.

    Ownership is enforced by requiring both merchant_id and product_id in
    every query, making cross-merchant or cross-product access structurally
    impossible through this interface.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: ProductImageEntity) -> ProductImageEntity:
        stmt = select(orm.Product.id).where(
            orm.Product.id == entity.product_id,
            orm.Product.merchant_id == entity.merchant_id,
        )
        if self._session.scalars(stmt).first() is None:
            raise AppError(
                ErrorCode.NOT_FOUND,
                "Product not found or does not belong to this merchant.",
                status_code=404,
            )

        now = _now_utc()
        row = orm.ProductImage(
            id=entity.id,
            merchant_id=entity.merchant_id,
            product_id=entity.product_id,
            storage_path=entity.storage_path,
            public_url=entity.public_url,
            alt_text=entity.alt_text,
            sort_order=entity.sort_order,
            created_at=now,
        )
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "Image at this sort_order already exists for the product.",
                status_code=409,
            ) from exc
        return _orm_product_image_to_entity(row)

    def get(
        self, merchant_id: str, product_id: str, image_id: str
    ) -> ProductImageEntity | None:
        stmt = select(orm.ProductImage).where(
            orm.ProductImage.id == image_id,
            orm.ProductImage.product_id == product_id,
            orm.ProductImage.merchant_id == merchant_id,  # tenant guard
        )
        row = self._session.scalars(stmt).first()
        return _orm_product_image_to_entity(row) if row is not None else None

    def list_for_product(
        self, merchant_id: str, product_id: str
    ) -> list[ProductImageEntity]:
        stmt = (
            select(orm.ProductImage)
            .where(
                orm.ProductImage.product_id == product_id,
                orm.ProductImage.merchant_id == merchant_id,  # tenant guard
            )
            .order_by(orm.ProductImage.sort_order)
        )
        return [_orm_product_image_to_entity(r) for r in self._session.scalars(stmt)]

    def delete(self, merchant_id: str, product_id: str, image_id: str) -> None:
        stmt = select(orm.ProductImage).where(
            orm.ProductImage.id == image_id,
            orm.ProductImage.product_id == product_id,
            orm.ProductImage.merchant_id == merchant_id,  # tenant guard
        )
        row = self._session.scalars(stmt).first()
        if row is not None:
            self._session.delete(row)
            self._session.flush()

    def count_for_product(self, merchant_id: str, product_id: str) -> int:
        return len(self.list_for_product(merchant_id, product_id))


# ---------------------------------------------------------------------------
# MerchantPolicy repository
# ---------------------------------------------------------------------------


class SqlAlchemyMerchantPolicyRepository:
    """SQLAlchemy implementation of MerchantPolicyRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_active(self, merchant_id: str) -> MerchantPolicyEntity | None:
        stmt = select(orm.MerchantPolicy).where(
            orm.MerchantPolicy.merchant_id == merchant_id,
            orm.MerchantPolicy.status == RecordStatus.ACTIVE.value,
        )
        row = self._session.scalars(stmt).first()
        return _orm_policy_to_entity(row) if row is not None else None

    def add(self, entity: MerchantPolicyEntity) -> MerchantPolicyEntity:
        now = _now_utc()
        row = orm.MerchantPolicy(
            id=entity.id,
            merchant_id=entity.merchant_id,
            mode=entity.mode.value,
            auto_accept_max_minor=(
                entity.auto_accept_max.amount_minor
                if entity.auto_accept_max is not None
                else None
            ),
            currency=(
                entity.auto_accept_max.currency
                if entity.auto_accept_max is not None
                else None
            ),
            version=entity.version,
            status=entity.status.value,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "Policy version already exists for this merchant.",
                status_code=409,
            ) from exc
        return _orm_policy_to_entity(row)

    def update(self, entity: MerchantPolicyEntity) -> MerchantPolicyEntity:
        stmt = select(orm.MerchantPolicy).where(
            orm.MerchantPolicy.id == entity.id,
            orm.MerchantPolicy.merchant_id == entity.merchant_id,  # tenant guard
        )
        row = self._session.scalars(stmt).first()
        if row is None:
            raise AppError(
                ErrorCode.NOT_FOUND,
                "Policy not found or does not belong to this merchant.",
                status_code=404,
            )
        now = _now_utc()
        row.mode = entity.mode.value
        row.auto_accept_max_minor = (
            entity.auto_accept_max.amount_minor
            if entity.auto_accept_max is not None
            else None
        )
        row.currency = (
            entity.auto_accept_max.currency
            if entity.auto_accept_max is not None
            else None
        )
        row.version = entity.version
        row.status = entity.status.value
        row.updated_at = now
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "Policy version already exists for this merchant.",
                status_code=409,
            ) from exc
        return _orm_policy_to_entity(row)
