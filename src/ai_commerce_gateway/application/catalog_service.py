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
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.core.ids import new_id
from ai_commerce_gateway.domain.enums import ActorType, MerchantRole, ProductStatus, RecordStatus
from ai_commerce_gateway.domain.merchant import CreateMerchantDomain
from ai_commerce_gateway.domain.product import MoneyMinor, ProductEntity
from ai_commerce_gateway.domain.repositories import MerchantRepository, ProductRepository


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _require_merchant_access(actor: ActorContext, merchant_id: str, required_roles: frozenset[MerchantRole] | set[MerchantRole] | None = None) -> None:  # noqa: E501
    if actor.actor_type == ActorType.SYSTEM:
        return
    if actor.actor_type != ActorType.MERCHANT_USER:
        raise AppError(ErrorCode.FORBIDDEN, "Only merchant users can access this resource.", status_code=403)  # noqa: E501
    
    if merchant_id not in actor.merchant_ids:
        raise AppError(ErrorCode.FORBIDDEN, "Access denied to this merchant.", status_code=403)
        
    if required_roles:
        if not (actor.roles & required_roles):
            raise AppError(ErrorCode.FORBIDDEN, "Insufficient role.", status_code=403)


class ApplicationMerchantCatalogService:
    def __init__(self, merchant_repo: MerchantRepository, product_repo: ProductRepository):
        self._merchant_repo = merchant_repo
        self._product_repo = product_repo

    def create_merchant(self, command: CreateMerchantCommand, actor: ActorContext) -> MerchantView:
        if actor.actor_type not in (ActorType.SYSTEM, ActorType.PLATFORM):
            raise AppError(ErrorCode.FORBIDDEN, "Only SYSTEM or PLATFORM can create merchants.", status_code=403)  # noqa: E501
            
        merchant_id = new_id("mer")
        domain_cmd = CreateMerchantDomain(
            id=merchant_id,
            name=command.name,
            idempotency_key=command.idempotency_key
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
                raise AppError(ErrorCode.FORBIDDEN, "Access denied to this merchant.", status_code=403)
            
            prod = None
            for m_id in actor.merchant_ids:
                prod = self._product_repo.get_by_id(m_id, product_id)
                if prod is not None:
                    break
            
            if prod is None:
                raise AppError(ErrorCode.NOT_FOUND, "Product not found", status_code=404)
            
            _require_merchant_access(actor, prod.merchant_id)
        else:
            raise AppError(ErrorCode.FORBIDDEN, "Only merchant users can access this resource.", status_code=403)

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
            images=()
        )


    def list_products(self, merchant_id: str, actor: ActorContext, cursor: str | None = None) -> ProductPage:  # noqa: E501
        _require_merchant_access(actor, merchant_id)
        limit = 50
        products = self._product_repo.list_for_merchant(merchant_id, cursor=cursor, limit=limit)
        
        items = []
        for prod in products:
            items.append(ProductView(
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
                images=()
            ))
            
        next_cursor = items[-1].id if len(items) == limit else None
        return ProductPage(items=tuple(items), next_cursor=next_cursor)

    def create_product(self, command: CreateProductCommand, actor: ActorContext) -> ProductView:
        _require_merchant_access(actor, command.merchant_id, frozenset([MerchantRole.ADMIN, MerchantRole.EDITOR]))  # noqa: E501
        
        # Check SKU uniqueness
        if self._product_repo.sku_exists_for_merchant(command.merchant_id, command.sku):
            raise AppError(ErrorCode.VALIDATION_ERROR, "SKU already exists for merchant", status_code=409)  # noqa: E501
            
        product_id = new_id("prod")
        now = _now()
        
        prod = ProductEntity(
            id=product_id,
            merchant_id=command.merchant_id,
            sku=command.sku,
            title=command.title,
            description=command.description,
            category=command.category,
            price=MoneyMinor(amount_minor=command.price.amount_minor, currency=command.price.currency),  # noqa: E501
            available_quantity=command.available_quantity,
            status=ProductStatus.DRAFT,
            version=1,
            created_at=now,
            updated_at=now
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
            images=()
        )

    def update_product(self, command: UpdateProductCommand, actor: ActorContext) -> ProductView:
        _require_merchant_access(actor, command.merchant_id, frozenset([MerchantRole.ADMIN, MerchantRole.EDITOR]))  # noqa: E501
        
        prod = self._product_repo.get_by_id(command.merchant_id, command.product_id)
        if not prod:
            raise AppError(ErrorCode.NOT_FOUND, "Product not found", status_code=404)
            
        if prod.version != command.expected_version:
            raise AppError(ErrorCode.VALIDATION_ERROR, "Version mismatch (stale write)", status_code=409)  # noqa: E501
            
        updated_prod = ProductEntity(
            id=prod.id,
            merchant_id=prod.merchant_id,
            sku=prod.sku,
            title=command.title if command.title is not None else prod.title,
            description=command.description if command.description is not None else prod.description,  # noqa: E501
            category=command.category if command.category is not None else prod.category,
            price=MoneyMinor(amount_minor=command.price.amount_minor, currency=command.price.currency) if command.price is not None else prod.price,  # noqa: E501
            available_quantity=command.available_quantity if command.available_quantity is not None else prod.available_quantity,  # noqa: E501
            status=prod.status,
            version=prod.version + 1,
            created_at=prod.created_at,
            updated_at=_now()
        )
        
        self._product_repo.update(updated_prod)
        
        return ProductView(
            id=updated_prod.id,
            merchant_id=updated_prod.merchant_id,
            sku=updated_prod.sku,
            title=updated_prod.title,
            description=updated_prod.description,
            category=updated_prod.category,
            price=Money(amount_minor=updated_prod.price.amount_minor, currency=updated_prod.price.currency),  # noqa: E501
            available_quantity=updated_prod.available_quantity,
            status=updated_prod.status,
            version=updated_prod.version,
            images=()
        )

    def publish_product(self, command: SetProductPublicationCommand, actor: ActorContext) -> ProductView:  # noqa: E501
        raise NotImplementedError("Publication is scope of A3")

    def unpublish_product(self, command: SetProductPublicationCommand, actor: ActorContext) -> ProductView:  # noqa: E501
        raise NotImplementedError("Publication is scope of A3")

    def add_product_image(self, command: AddProductImageCommand, actor: ActorContext) -> ProductImageView:  # noqa: E501
        raise NotImplementedError("Image storage is scope of A5")

    def delete_product_image(self, command: DeleteProductImageCommand, actor: ActorContext) -> None:
        raise NotImplementedError("Image storage is scope of A5")
