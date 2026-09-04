from ai_commerce_gateway.contracts.models import (
    ActorContext,
    CatalogSearchQuery,
    CatalogSearchResult,
    Money,
    ProductView,
)
from ai_commerce_gateway.contracts.services import CatalogService
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ProductStatus
from ai_commerce_gateway.domain.product import ProductEntity
from ai_commerce_gateway.domain.repositories import ProductRepository


class ApplicationCatalogService(CatalogService):
    def __init__(self, product_repo: ProductRepository):
        self._product_repo = product_repo

    def _to_view(self, prod: ProductEntity) -> ProductView:
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

    def search(self, query: CatalogSearchQuery, actor: ActorContext) -> CatalogSearchResult:
        fetch_limit = 100
        entities = self._product_repo.list_published(
            merchant_id=query.merchant_id,
            cursor=query.cursor,
            limit=fetch_limit,
        )
        
        filtered = []
        for entity in entities:
            if query.query:
                q_lower = query.query.lower()
                if q_lower not in entity.title.lower() and q_lower not in entity.description.lower():  # noqa: E501
                    continue
            
            if query.category and entity.category != query.category:
                continue
            
            if query.min_price_minor is not None and entity.price.amount_minor < query.min_price_minor:  # noqa: E501
                continue
                
            if query.max_price_minor is not None and entity.price.amount_minor > query.max_price_minor:  # noqa: E501
                continue
                
            if query.currency and entity.price.currency != query.currency:
                continue
                
            filtered.append(entity)
            if len(filtered) == query.limit:
                break
                
        items = tuple(self._to_view(e) for e in filtered)
        
        next_cursor = None
        if len(filtered) == query.limit:
            next_cursor = filtered[-1].id
        elif len(entities) == fetch_limit:
            next_cursor = entities[-1].id
            
        return CatalogSearchResult(items=items, next_cursor=next_cursor)

    def get_product(self, merchant_id: str, product_id: str, actor: ActorContext) -> ProductView:
        prod = self._product_repo.get_by_id(merchant_id, product_id)
        if not prod or prod.status != ProductStatus.PUBLISHED:
            raise AppError(ErrorCode.NOT_FOUND, "Product not found or not published", status_code=404)  # noqa: E501
            
        return self._to_view(prod)
