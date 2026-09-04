"""Merchant-facing HTTP routes.

The extraction route is D-010's propose-only seam: it returns a structured
draft for merchant review and never persists anything.  Publication always
flows through the frozen ``MerchantCatalogService``.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from ai_commerce_gateway.application.product_draft_extraction import (
    LLMProductDraftExtractor,
    ProductDraftExtractor,
    StubProductDraftExtractor,
)
from ai_commerce_gateway.contracts.models import ActorContext
from ai_commerce_gateway.core.config import get_settings
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ActorType, MerchantRole


def get_product_draft_extractor() -> ProductDraftExtractor:
    """LLM-backed extractor when a key is configured, stub otherwise."""
    settings = get_settings()
    if settings.llm_api_key:
        return LLMProductDraftExtractor(
            provider_url=settings.llm_provider_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )
    return StubProductDraftExtractor()


class ExtractDraftRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class ExtractDraftResponse(BaseModel):
    draft: dict[str, Any]
    persisted: bool = False
    note: str = (
        "Proposal only. Review and publish via the catalog; "
        "this endpoint never writes."
    )


def _demo_actor(
    merchant_id: str,
    user_id: str | None,
    roles_header: str | None,
) -> ActorContext:
    """Demo identity plumbing — real merchant auth arrives with A6 auth work.

    Identity is derived server-side from transport headers, never from tool
    or body inputs.  Roles default to ADMIN for the demo; production must
    resolve membership and roles from the database.
    """
    roles = frozenset({MerchantRole.ADMIN})
    if roles_header:
        parsed = {
            role.strip().upper() for role in roles_header.split(",") if role.strip()
        }
        known = {role.value for role in MerchantRole}
        roles = frozenset(
            {MerchantRole(role) for role in parsed if role in known}
        ) or roles
    return ActorContext(
        actor_id=user_id or "merchant_demo_001",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset({merchant_id}),
        roles=roles,
        correlation_id="",
    )


def _require_catalog_roles(actor: ActorContext) -> None:
    if not actor.roles & {MerchantRole.ADMIN, MerchantRole.EDITOR}:
        raise AppError(
            ErrorCode.FORBIDDEN,
            "Insufficient role for catalog drafting.",
            status_code=403,
        )


router = APIRouter(prefix="/merchants", tags=["merchant-catalog"])


@router.post("/{merchant_id}/products/extract-draft", response_model=ExtractDraftResponse)
def extract_product_draft(
    merchant_id: str,
    request: ExtractDraftRequest,
    extractor: Annotated[
        ProductDraftExtractor,
        Depends(get_product_draft_extractor),
    ],
    x_merchant_user_id: Annotated[str | None, Header()] = None,
    x_merchant_roles: Annotated[str | None, Header()] = None,
) -> ExtractDraftResponse:
    """Extract a structured product draft from merchant natural language.

    D-010: propose-only.  The returned draft is NOT persisted; the merchant
    reviews it and creation/publication flow through the frozen catalog
    services (create_product → DRAFT → review → publish_product).
    """
    actor = _demo_actor(merchant_id, x_merchant_user_id, x_merchant_roles)
    if merchant_id not in actor.merchant_ids:
        raise AppError(
            ErrorCode.FORBIDDEN, "Access denied to this merchant.", status_code=403
        )
    _require_catalog_roles(actor)

    draft = extractor.extract(request.text)
    return ExtractDraftResponse(draft=draft.model_dump())