from dataclasses import replace
from datetime import UTC, datetime

from ai_commerce_gateway.contracts.models import (
    ActorContext,
    AddProductImageCommand,
    CreateMerchantCommand,
    CreateProductCommand,
    DeleteProductImageCommand,
    MerchantView,
    Money,
    ProductImageView,
    ProductPage,
    ProductView,
    SetProductPublicationCommand,
    UpdateProductCommand,
)
from ai_commerce_gateway.contracts.services import StorageService
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.core.ids import new_id
from ai_commerce_gateway.domain.enums import ActorType, MerchantRole, ProductStatus, RecordStatus
from ai_commerce_gateway.domain.merchant import CreateMerchantDomain
from ai_commerce_gateway.domain.product import MoneyMinor, ProductEntity, ProductImageEntity
from ai_commerce_gateway.domain.repositories import (
    MerchantRepository,
    ProductImageRepository,
    ProductRepository,
)

ALLOWED_IMAGE_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _to_product_view(
    prod: ProductEntity,
    images: tuple[ProductImageView, ...] = (),
) -> ProductView:
    return ProductView(
        id=prod.id,
        merchant_id=prod.merchant_id,
        sku=prod.sku,
        title=prod.title,
        description=prod.description,
        category=prod.category,
        price=Money(amount_minor=prod.price.amount_minor, currency=prod.price.currency),
        available_quantity=prod.available_quantity,
        status=prod.status,
        version=prod.version,
        images=images,
    )


def _require_merchant_access(
    actor: ActorContext,
    merchant_id: str,
    required_roles: frozenset[MerchantRole] | set[MerchantRole] | None = None,
) -> None:  # noqa: E501
    if actor.actor_type == ActorType.SYSTEM:
        return
    if actor.actor_type != ActorType.MERCHANT_USER:
        raise AppError(
            ErrorCode.FORBIDDEN, "Only merchant users can access this resource.", status_code=403
        )  # noqa: E501

    if merchant_id not in actor.merchant_ids:
        raise AppError(ErrorCode.FORBIDDEN, "Access denied to this merchant.", status_code=403)

    if required_roles:
        if not (actor.roles & required_roles):
            raise AppError(ErrorCode.FORBIDDEN, "Insufficient role.", status_code=403)


class ApplicationMerchantCatalogService:
    def __init__(
        self,
        merchant_repo: MerchantRepository,
        product_repo: ProductRepository,
        image_repo: ProductImageRepository | None = None,
        storage_svc: StorageService | None = None,
    ) -> None:
        self._merchant_repo = merchant_repo
        self._product_repo = product_repo
        self._image_repo = image_repo
        self._storage_svc = storage_svc

    def _get_product_images(
        self, merchant_id: str, product_id: str
    ) -> tuple[ProductImageView, ...]:
        if self._image_repo is None:
            return ()
        entities = self._image_repo.list_for_product(merchant_id, product_id)
        return tuple(
            ProductImageView(
                id=img.id,
                url=img.public_url or "",
                alt_text=img.alt_text,
                sort_order=img.sort_order,
            )
            for img in entities
        )

    def create_merchant(self, command: CreateMerchantCommand, actor: ActorContext) -> MerchantView:
        if actor.actor_type not in (ActorType.SYSTEM, ActorType.PLATFORM):
            raise AppError(
                ErrorCode.FORBIDDEN,
                "Only SYSTEM or PLATFORM can create merchants.",
                status_code=403,
            )  # noqa: E501

        merchant_id = new_id("mer")
        domain_cmd = CreateMerchantDomain(
            id=merchant_id, name=command.name, idempotency_key=command.idempotency_key
        )
        self._merchant_repo.add(domain_cmd)
        return MerchantView(id=merchant_id, name=command.name, status=RecordStatus.ACTIVE.value)

    def get_merchant(self, merchant_id: str, actor: ActorContext) -> MerchantView:
        _require_merchant_access(actor, merchant_id)
        mer = self._merchant_repo.get_by_id(merchant_id)
        if not mer:
            raise AppError(ErrorCode.NOT_FOUND, "Merchant not found", status_code=404)
        return MerchantView(id=mer.id, name=mer.name, status=mer.status.value)

    def get_product(self, product_id: str, actor: ActorContext) -> ProductView:
        if actor.actor_type == ActorType.SYSTEM:
            raise NotImplementedError("System actor lookup without merchant_id not implemented")
        elif actor.actor_type == ActorType.MERCHANT_USER:
            if not actor.merchant_ids:
                raise AppError(
                    ErrorCode.FORBIDDEN, "Access denied to this merchant.", status_code=403
                )  # noqa: E501

            prod = None
            for m_id in actor.merchant_ids:
                prod = self._product_repo.get_by_id(m_id, product_id)
                if prod is not None:
                    break

            if prod is None:
                raise AppError(ErrorCode.NOT_FOUND, "Product not found", status_code=404)

            _require_merchant_access(actor, prod.merchant_id)
        else:
            raise AppError(
                ErrorCode.FORBIDDEN,
                "Only merchant users can access this resource.",
                status_code=403,
            )  # noqa: E501

        images = self._get_product_images(prod.merchant_id, prod.id)
        return _to_product_view(prod, images=images)

    def list_products(
        self, merchant_id: str, actor: ActorContext, cursor: str | None = None
    ) -> ProductPage:  # noqa: E501
        _require_merchant_access(actor, merchant_id)
        limit = 50
        products = self._product_repo.list_for_merchant(merchant_id, cursor=cursor, limit=limit)

        items = []
        for prod in products:
            images = self._get_product_images(merchant_id, prod.id)
            items.append(_to_product_view(prod, images=images))

        next_cursor = items[-1].id if len(items) == limit else None
        return ProductPage(items=tuple(items), next_cursor=next_cursor)

    def create_product(self, command: CreateProductCommand, actor: ActorContext) -> ProductView:
        _require_merchant_access(
            actor, command.merchant_id, frozenset([MerchantRole.ADMIN, MerchantRole.EDITOR])
        )  # noqa: E501

        # Check SKU uniqueness
        if self._product_repo.sku_exists_for_merchant(command.merchant_id, command.sku):
            raise AppError(
                ErrorCode.VALIDATION_ERROR, "SKU already exists for merchant", status_code=409
            )  # noqa: E501

        product_id = new_id("prod")
        now = _now()

        prod = ProductEntity(
            id=product_id,
            merchant_id=command.merchant_id,
            sku=command.sku,
            title=command.title,
            description=command.description,
            category=command.category,
            price=MoneyMinor(
                amount_minor=command.price.amount_minor, currency=command.price.currency
            ),  # noqa: E501
            available_quantity=command.available_quantity,
            status=ProductStatus.DRAFT,
            version=1,
            created_at=now,
            updated_at=now,
        )

        self._product_repo.add(prod)

        return ProductView(
            id=prod.id,
            merchant_id=prod.merchant_id,
            sku=prod.sku,
            title=prod.title,
            description=prod.description,
            category=prod.category,
            price=Money(amount_minor=prod.price.amount_minor, currency=prod.price.currency),
            available_quantity=prod.available_quantity,
            status=prod.status,
            version=prod.version,
            images=(),
        )

    def update_product(self, command: UpdateProductCommand, actor: ActorContext) -> ProductView:
        _require_merchant_access(
            actor, command.merchant_id, frozenset([MerchantRole.ADMIN, MerchantRole.EDITOR])
        )  # noqa: E501

        prod = self._product_repo.get_by_id(command.merchant_id, command.product_id)
        if not prod:
            raise AppError(ErrorCode.NOT_FOUND, "Product not found", status_code=404)

        if prod.version != command.expected_version:
            raise AppError(
                ErrorCode.VALIDATION_ERROR, "Version mismatch (stale write)", status_code=409
            )  # noqa: E501

        updated_prod = ProductEntity(
            id=prod.id,
            merchant_id=prod.merchant_id,
            sku=prod.sku,
            title=command.title if command.title is not None else prod.title,
            description=command.description
            if command.description is not None
            else prod.description,  # noqa: E501
            category=command.category if command.category is not None else prod.category,
            price=MoneyMinor(
                amount_minor=command.price.amount_minor, currency=command.price.currency
            )
            if command.price is not None
            else prod.price,  # noqa: E501
            available_quantity=command.available_quantity
            if command.available_quantity is not None
            else prod.available_quantity,  # noqa: E501
            status=prod.status,
            version=prod.version + 1,
            created_at=prod.created_at,
            updated_at=_now(),
        )

        self._product_repo.update(updated_prod)
        images = self._get_product_images(updated_prod.merchant_id, updated_prod.id)
        return _to_product_view(updated_prod, images=images)

    def publish_product(
        self, command: SetProductPublicationCommand, actor: ActorContext
    ) -> ProductView:
        _require_merchant_access(
            actor,
            command.merchant_id,
            required_roles=frozenset([MerchantRole.ADMIN, MerchantRole.EDITOR]),
        )

        prod = self._product_repo.get_by_id(command.merchant_id, command.product_id)
        if not prod:
            raise AppError(ErrorCode.NOT_FOUND, "Product not found", status_code=404)

        # We rely on DB for concurrent check, but do a pre-check here
        if prod.version != command.expected_version:
            raise AppError(
                ErrorCode.VALIDATION_ERROR, "Version mismatch (stale write)", status_code=409
            )

        prod = replace(
            prod,
            status=ProductStatus.PUBLISHED,
            version=prod.version + 1,
            updated_at=_now(),
        )

        updated_prod = self._product_repo.update(prod)
        images = self._get_product_images(updated_prod.merchant_id, updated_prod.id)
        return _to_product_view(updated_prod, images=images)

    def unpublish_product(
        self, command: SetProductPublicationCommand, actor: ActorContext
    ) -> ProductView:
        _require_merchant_access(
            actor,
            command.merchant_id,
            required_roles=frozenset([MerchantRole.ADMIN, MerchantRole.EDITOR]),
        )

        prod = self._product_repo.get_by_id(command.merchant_id, command.product_id)
        if not prod:
            raise AppError(ErrorCode.NOT_FOUND, "Product not found", status_code=404)

        if prod.version != command.expected_version:
            raise AppError(
                ErrorCode.VALIDATION_ERROR, "Version mismatch (stale write)", status_code=409
            )

        prod = replace(
            prod,
            status=ProductStatus.UNPUBLISHED,
            version=prod.version + 1,
            updated_at=_now(),
        )

        updated_prod = self._product_repo.update(prod)
        images = self._get_product_images(updated_prod.merchant_id, updated_prod.id)
        return _to_product_view(updated_prod, images=images)

    def add_product_image(
        self, command: AddProductImageCommand, actor: ActorContext
    ) -> ProductImageView:
        _require_merchant_access(
            actor,
            command.merchant_id,
            required_roles=frozenset([MerchantRole.ADMIN, MerchantRole.EDITOR]),
        )

        if self._image_repo is None or self._storage_svc is None:
            raise AppError(
                ErrorCode.INTERNAL_ERROR,
                "Image storage service is not configured.",
                status_code=500,
            )

        prod = self._product_repo.get_by_id(command.merchant_id, command.product_id)
        if not prod:
            raise AppError(ErrorCode.NOT_FOUND, "Product not found.", status_code=404)

        if command.content_type.lower() not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                f"Unsupported content type '{command.content_type}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_IMAGE_CONTENT_TYPES))}",
                status_code=400,
            )

        if len(command.content) == 0:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "Image content cannot be empty.",
                status_code=400,
            )

        if len(command.content) > MAX_IMAGE_SIZE_BYTES:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "Image size exceeds 5MB limit.",
                status_code=400,
            )

        current_count = self._image_repo.count_for_product(command.merchant_id, command.product_id)
        if current_count >= 3:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "Maximum of 3 images allowed per product.",
                status_code=400,
            )

        existing_images = self._image_repo.list_for_product(command.merchant_id, command.product_id)
        if any(img.sort_order == command.sort_order for img in existing_images):
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                f"Image with sort_order {command.sort_order} already exists for this product.",
                status_code=409,
            )

        stored = self._storage_svc.upload_product_image(
            merchant_id=command.merchant_id,
            product_id=command.product_id,
            filename=command.filename,
            content_type=command.content_type,
            content=command.content,
        )

        image_id = new_id("pimg")
        entity = ProductImageEntity(
            id=image_id,
            merchant_id=command.merchant_id,
            product_id=command.product_id,
            storage_path=stored.storage_path,
            public_url=stored.public_url,
            alt_text=command.alt_text,
            sort_order=command.sort_order,
            created_at=_now(),
        )

        try:
            saved = self._image_repo.add(entity)
        except Exception:
            self._storage_svc.delete_product_image(storage_path=stored.storage_path)
            raise

        return ProductImageView(
            id=saved.id,
            url=saved.public_url or "",
            alt_text=saved.alt_text,
            sort_order=saved.sort_order,
        )

    def delete_product_image(self, command: DeleteProductImageCommand, actor: ActorContext) -> None:
        _require_merchant_access(
            actor,
            command.merchant_id,
            required_roles=frozenset([MerchantRole.ADMIN, MerchantRole.EDITOR]),
        )

        if self._image_repo is None or self._storage_svc is None:
            raise AppError(
                ErrorCode.INTERNAL_ERROR,
                "Image storage service is not configured.",
                status_code=500,
            )

        prod = self._product_repo.get_by_id(command.merchant_id, command.product_id)
        if not prod:
            raise AppError(ErrorCode.NOT_FOUND, "Product not found.", status_code=404)

        img = self._image_repo.get(command.merchant_id, command.product_id, command.image_id)
        if not img:
            raise AppError(ErrorCode.NOT_FOUND, "Product image not found.", status_code=404)

        self._image_repo.delete(command.merchant_id, command.product_id, command.image_id)
        self._storage_svc.delete_product_image(storage_path=img.storage_path)
