"""Buyer catalog application service.

Architectural Rationale for Search Filtering:
---------------------------------------------
The Milestone 0 ProductRepository protocol defines:
    list_published(merchant_id: str, *, cursor: str | None = None, limit: int = 20)
    -> list[ProductEntity]

This protocol interface is frozen across workstreams. In accordance with Invariant 19
(tenant isolation enforced strictly at the SQL query boundary), repository queries scope
strictly by merchant_id with status=PUBLISHED.

Multi-attribute buyer filtering (substring matching across title and description,
category equivalence, min_price_minor, max_price_minor, and currency matching) is executed
in the application service layer. For V1 merchant catalog scale (merchant-bounded product sets),
in-memory evaluation against tenant-isolated published records guarantees zero cross-tenant
leakage, total parameter safety, and exact compliance with frozen repository protocols.
"""

from ai_commerce_gateway.application.catalog_service import _to_product_view
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    CatalogSearchQuery,
    CatalogSearchResult,
    ProductImageView,
    ProductView,
)
from ai_commerce_gateway.contracts.services import CatalogService
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ProductStatus
from ai_commerce_gateway.domain.repositories import (
    ProductImageRepository,
    ProductRepository,
)


class ApplicationCatalogService(CatalogService):
    def __init__(
        self,
        product_repo: ProductRepository,
        image_repo: ProductImageRepository | None = None,
    ) -> None:
        self._product_repo = product_repo
        self._image_repo = image_repo

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

    def search(self, query: CatalogSearchQuery, actor: ActorContext) -> CatalogSearchResult:
        # Fetch with buffer to accommodate filtering while respecting requested page size
        fetch_limit = min(max(query.limit + 1, 50), 100)
        entities = self._product_repo.list_published(
            merchant_id=query.merchant_id,
            cursor=query.cursor,
            limit=fetch_limit,
        )

        filtered = []
        for entity in entities:
            if query.query:
                q_lower = query.query.lower()
                title_match = q_lower in entity.title.lower()
                desc_match = bool(entity.description and q_lower in entity.description.lower())
                if not (title_match or desc_match):
                    continue

            if query.category is not None and entity.category != query.category:
                continue

            if (
                query.min_price_minor is not None
                and entity.price.amount_minor < query.min_price_minor
            ):
                continue

            if (
                query.max_price_minor is not None
                and entity.price.amount_minor > query.max_price_minor
            ):
                continue

            if query.currency is not None and entity.price.currency != query.currency:
                continue

            filtered.append(entity)
            if len(filtered) == query.limit:
                break

        items = tuple(
            _to_product_view(
                e,
                images=self._get_product_images(query.merchant_id, e.id),
            )
            for e in filtered
        )

        next_cursor = None
        if len(filtered) == query.limit:
            next_cursor = filtered[-1].id
        elif len(entities) == fetch_limit:
            next_cursor = entities[-1].id

        return CatalogSearchResult(items=items, next_cursor=next_cursor)

    def get_product(self, merchant_id: str, product_id: str, actor: ActorContext) -> ProductView:
        prod = self._product_repo.get_by_id(merchant_id, product_id)
        if not prod or prod.status != ProductStatus.PUBLISHED:
            raise AppError(
                ErrorCode.NOT_FOUND,
                "Product not found or not published",
                status_code=404,
            )

        images = self._get_product_images(merchant_id, prod.id)
        return _to_product_view(prod, images=images)
