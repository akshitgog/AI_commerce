"""Idempotent wrapper around the frozen ``MerchantCatalogService``.

Wraps ``create_product``, ``update_product``, ``publish_product`` and
``unpublish_product`` with durable fingerprint-scoped idempotency backed by
the shared ``idempotency_records`` table.  A reused idempotency key with the
same fingerprint replays by re-fetching the product from the inner service;
a reused key with a *different* fingerprint is rejected.

All other ``MerchantCatalogService`` operations pass through unchanged.
This wrapper does NOT modify any shared contract or DTO.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime

from ai_commerce_gateway.contracts.models import (
    ActorContext,
    AddProductImageCommand,
    CreateMerchantCommand,
    CreateProductCommand,
    DeleteProductImageCommand,
    MerchantView,
    ProductImageView,
    ProductPage,
    ProductView,
    SetProductPublicationCommand,
    UpdateProductCommand,
)
from ai_commerce_gateway.contracts.services import MerchantCatalogService
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.core.ids import new_id
from ai_commerce_gateway.domain.idempotency import (
    CATALOG_CREATE_PRODUCT,
    CATALOG_PUBLISH_PRODUCT,
    CATALOG_UNPUBLISH_PRODUCT,
    CATALOG_UPDATE_PRODUCT,
    CatalogIdempotencyRecord,
    catalog_request_fingerprint,
    response_fingerprint,
)
from ai_commerce_gateway.domain.repositories import IdempotencyRepository


class IdempotentCatalogService:
    """Wraps a ``MerchantCatalogService`` with catalog-mutation idempotency."""

    def __init__(
        self,
        inner: MerchantCatalogService,
        idempotency_repo: IdempotencyRepository,
    ) -> None:
        self._inner = inner
        self._idempotency_repo = idempotency_repo

    # -- passthrough operations -------------------------------------------

    def create_merchant(
        self, command: CreateMerchantCommand, actor: ActorContext
    ) -> MerchantView:
        return self._inner.create_merchant(command, actor)

    def get_merchant(self, merchant_id: str, actor: ActorContext) -> MerchantView:
        return self._inner.get_merchant(merchant_id, actor)

    def get_product(self, product_id: str, actor: ActorContext) -> ProductView:
        return self._inner.get_product(product_id, actor)

    def list_products(
        self, merchant_id: str, actor: ActorContext, cursor: str | None = None
    ) -> ProductPage:
        return self._inner.list_products(merchant_id, actor, cursor=cursor)

    def add_product_image(
        self, command: AddProductImageCommand, actor: ActorContext
    ) -> ProductImageView:
        return self._inner.add_product_image(command, actor)

    def delete_product_image(
        self, command: DeleteProductImageCommand, actor: ActorContext
    ) -> None:
        return self._inner.delete_product_image(command, actor)

    # -- idempotent mutations ---------------------------------------------

    def create_product(
        self, command: CreateProductCommand, actor: ActorContext
    ) -> ProductView:
        return self._idempotent(
            command_idempotency_key=command.idempotency_key,
            actor=actor,
            operation=CATALOG_CREATE_PRODUCT,
            merchant_id=command.merchant_id,
            product_id="",
            command_fields={
                "sku": command.sku,
                "title": command.title,
                "description": command.description,
                "category": command.category,
                "amount_minor": command.price.amount_minor,
                "currency": command.price.currency,
                "available_quantity": command.available_quantity,
            },
            execute=lambda: self._inner.create_product(command, actor),
        )

    def update_product(
        self, command: UpdateProductCommand, actor: ActorContext
    ) -> ProductView:
        return self._idempotent(
            command_idempotency_key=command.idempotency_key,
            actor=actor,
            operation=CATALOG_UPDATE_PRODUCT,
            merchant_id=command.merchant_id,
            product_id=command.product_id,
            command_fields={
                "expected_version": command.expected_version,
                "title": command.title,
                "description": command.description,
                "category": command.category,
                "amount_minor": (
                    command.price.amount_minor if command.price is not None else None
                ),
                "currency": command.price.currency if command.price is not None else None,
                "available_quantity": command.available_quantity,
            },
            execute=lambda: self._inner.update_product(command, actor),
        )

    def publish_product(
        self, command: SetProductPublicationCommand, actor: ActorContext
    ) -> ProductView:
        return self._idempotent(
            command_idempotency_key=command.idempotency_key,
            actor=actor,
            operation=CATALOG_PUBLISH_PRODUCT,
            merchant_id=command.merchant_id,
            product_id=command.product_id,
            command_fields={
                "action": "publish",
                "expected_version": command.expected_version,
            },
            execute=lambda: self._inner.publish_product(command, actor),
        )

    def unpublish_product(
        self, command: SetProductPublicationCommand, actor: ActorContext
    ) -> ProductView:
        return self._idempotent(
            command_idempotency_key=command.idempotency_key,
            actor=actor,
            operation=CATALOG_UNPUBLISH_PRODUCT,
            merchant_id=command.merchant_id,
            product_id=command.product_id,
            command_fields={
                "action": "unpublish",
                "expected_version": command.expected_version,
            },
            execute=lambda: self._inner.unpublish_product(command, actor),
        )

    # -- core idempotent gate ---------------------------------------------

    def _idempotent(
        self,
        *,
        command_idempotency_key: str,
        actor: ActorContext,
        operation: str,
        merchant_id: str,
        product_id: str,
        command_fields: dict[str, object],
        execute: Callable[[], ProductView],
    ) -> ProductView:
        fingerprint = catalog_request_fingerprint(
            actor_id=actor.actor_id,
            operation=operation,
            merchant_id=merchant_id,
            product_id=product_id,
            idempotency_key=command_idempotency_key,
            **command_fields,
        )

        record = CatalogIdempotencyRecord(
            id=new_id("idem"),
            actor_id=actor.actor_id,
            operation=operation,
            idempotency_key=command_idempotency_key,
            request_fingerprint=fingerprint,
            resource_type=None,
            resource_id=None,
            response_code=None,
            response_body_hash=None,
            created_at=datetime.now(tz=UTC),
        )

        existing, is_new = self._idempotency_repo.claim(record)

        if not is_new:
            existing.require_same_request(fingerprint)
            if existing.resource_id is not None and existing.response_code == 200:
                return self._inner.get_product(existing.resource_id, actor)
            raise AppError(
                ErrorCode.IDEMPOTENCY_KEY_REUSED,
                "Idempotency key was already used for another request.",
                status_code=409,
            )

        result = execute()

        body = json.dumps(
            {"ok": True, "product_id": result.id},
            sort_keys=True,
            separators=(",", ":"),
        )
        self._idempotency_repo.save_result(
            existing.id,
            resource_type="product",
            resource_id=result.id,
            response_code=200,
            response_body_hash=response_fingerprint(body),
        )
        return result