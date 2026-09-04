"""Merchant-facing HTTP routes (P0-2/P0-5/P0-6).

Every merchant route derives identity from a server-side session token
(``Authorization: Bearer``).  No identity, role or merchant claim is ever
read from request input.  Mutations flow through the idempotent catalog
wrapper (A7); publication additionally requires a dashboard-issued
confirmation token (P0-5) that is verified and stripped here before the
frozen ``MerchantCatalogService`` command is invoked.

Transaction/audit read seams depend on the frozen ``TransactionService``,
whose implementation is owned by the transaction lane and becomes available
at integration (07); until then they answer 501 instead of fake data.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai_commerce_gateway.application.catalog_idempotency import IdempotentCatalogService
from ai_commerce_gateway.application.catalog_service import ApplicationMerchantCatalogService
from ai_commerce_gateway.application.merchant_sessions import MerchantSession
from ai_commerce_gateway.application.policy_service import ApplicationMerchantPolicyService
from ai_commerce_gateway.application.product_draft_extraction import (
    LLMProductDraftExtractor,
    ProductDraftExtractor,
    StubProductDraftExtractor,
)
from ai_commerce_gateway.application.publication_confirmation_service import (
    PublicationConfirmationService,
)
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    CreateProductCommand,
    MerchantPolicyView,
    MerchantReviewPage,
    Money,
    ProductPage,
    ProductView,
    SetProductPublicationCommand,
    UpdateMerchantPolicyCommand,
    UpdateProductCommand,
)
from ai_commerce_gateway.core.config import get_settings
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ActorType, MerchantRole, PolicyMode
from ai_commerce_gateway.domain.publication_confirmation import (
    ACTION_PUBLISH,
    ACTION_UNPUBLISH,
    PublicationConfirmationClaim,
)
from ai_commerce_gateway.infrastructure.database.merchant_confirmations import (
    SqlAlchemyUsedConfirmationStore,
)
from ai_commerce_gateway.infrastructure.database.merchant_idempotency import (
    SqlAlchemyMerchantIdempotencyRepository,
)
from ai_commerce_gateway.infrastructure.database.merchant_repositories import (
    SqlAlchemyMerchantPolicyRepository,
    SqlAlchemyMerchantRepository,
    SqlAlchemyMerchantUserRepository,
    SqlAlchemyProductImageRepository,
    SqlAlchemyProductRepository,
)
from ai_commerce_gateway.infrastructure.database.merchant_sessions import (
    SqlAlchemyMerchantSessionService,
)

router = APIRouter(prefix="/merchants", tags=["merchant"])


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def get_db_session(request: Request) -> Iterator[Session]:
    factory = request.app.state.session_factory
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db_session)]


def get_session_service(
    db: DbSession,
) -> SqlAlchemyMerchantSessionService:
    return SqlAlchemyMerchantSessionService(SqlAlchemyMerchantUserRepository(db), db)


SessionService = Annotated[SqlAlchemyMerchantSessionService, Depends(get_session_service)]


def get_merchant_actor(
    merchant_id: str,
    request: Request,
    sessions: SessionService,
    authorization: Annotated[str | None, Header()] = None,
) -> ActorContext:
    """Resolve the caller's identity exclusively from a server-side session."""
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(
            ErrorCode.UNAUTHENTICATED,
            "A merchant session bearer token is required.",
            status_code=401,
        )
    token = authorization.removeprefix("Bearer ").strip()
    session = sessions.resolve(token)
    if session is None:
        raise AppError(
            ErrorCode.UNAUTHENTICATED,
            "Invalid or expired merchant session.",
            status_code=401,
        )
    if session.merchant_id != merchant_id:
        raise AppError(
            ErrorCode.FORBIDDEN,
            "Session is not scoped to this merchant.",
            status_code=403,
        )
    return _actor_from_session(session, request)


MerchantActor = Annotated[ActorContext, Depends(get_merchant_actor)]


def _actor_from_session(session: MerchantSession, request: Request) -> ActorContext:
    return ActorContext(
        actor_id=session.user_id,
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset({session.merchant_id}),
        roles=frozenset({session.role}),
        correlation_id=getattr(request.state, "correlation_id", ""),
    )


def _require_roles(actor: ActorContext, allowed: set[MerchantRole]) -> None:
    if not actor.roles & allowed:
        raise AppError(
            ErrorCode.FORBIDDEN, "Insufficient role.", status_code=403
        )


_CATALOG_WRITE_ROLES = {MerchantRole.ADMIN, MerchantRole.EDITOR}


def get_catalog_service(db: DbSession) -> IdempotentCatalogService:
    inner = ApplicationMerchantCatalogService(
        SqlAlchemyMerchantRepository(db),
        SqlAlchemyProductRepository(db),
        SqlAlchemyProductImageRepository(db),
        None,
    )
    return IdempotentCatalogService(inner, SqlAlchemyMerchantIdempotencyRepository(db))


CatalogSvc = Annotated[IdempotentCatalogService, Depends(get_catalog_service)]


def get_policy_service(db: DbSession) -> ApplicationMerchantPolicyService:
    return ApplicationMerchantPolicyService(
        SqlAlchemyMerchantPolicyRepository(db), session=db
    )


PolicySvc = Annotated[ApplicationMerchantPolicyService, Depends(get_policy_service)]


def get_confirmation_service(db: DbSession) -> PublicationConfirmationService:
    return PublicationConfirmationService(
        get_settings().publication_secret_value,
        used_store=SqlAlchemyUsedConfirmationStore(db),
    )


ConfirmationSvc = Annotated[
    PublicationConfirmationService, Depends(get_confirmation_service)
]


def get_product_draft_extractor() -> ProductDraftExtractor:
    settings = get_settings()
    if settings.llm_api_key:
        return LLMProductDraftExtractor(
            provider_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value(),
            model=settings.llm_model,
        )
    return StubProductDraftExtractor()


Extractor = Annotated[ProductDraftExtractor, Depends(get_product_draft_extractor)]


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class IssueSessionBody(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)


class CreateProductBody(BaseModel):
    sku: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    description: str
    category: str | None = None
    price: Money
    available_quantity: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=255)


class UpdateProductBody(BaseModel):
    expected_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=255)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = None
    price: Money | None = None
    available_quantity: int | None = Field(default=None, ge=0)


class PublicationActionBody(BaseModel):
    expected_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=255)
    confirmation_token: str = Field(min_length=1)


class IssueConfirmationBody(BaseModel):
    expected_version: int = Field(ge=1)
    action: Literal["PUBLISH", "UNPUBLISH"]


class ExtractDraftBody(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class UpdatePolicyBody(BaseModel):
    mode: PolicyMode
    auto_accept_max: Money | None = None
    expected_version: int | None = Field(default=None, ge=1)
    idempotency_key: str = Field(min_length=1, max_length=255)


# ---------------------------------------------------------------------------
# Sessions (auth boundary)
# ---------------------------------------------------------------------------

@router.post("/{merchant_id}/sessions", status_code=201)
def issue_session(
    merchant_id: str, body: IssueSessionBody, sessions: SessionService, request: Request
) -> dict[str, str]:
    """Issue a merchant session after server-side membership verification.

    Development authenticator: proves the user is a merchant member via the
    repository and derives roles from the membership record.  Production
    credential verification plugs into the same seam without route changes.
    """
    session = sessions.issue(
        merchant_id,
        body.user_id,
        correlation_id=getattr(request.state, "correlation_id", ""),
    )
    return {"session_token": session.token, "expires_at": session.expires_at.isoformat()}


@router.delete("/{merchant_id}/sessions", status_code=204)
def revoke_session(
    merchant_id: str,
    sessions: SessionService,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    if authorization and authorization.startswith("Bearer "):
        sessions.revoke(
            authorization.removeprefix("Bearer ").strip(),
            correlation_id=getattr(request.state, "correlation_id", ""),
        )


# ---------------------------------------------------------------------------
# Products CRUD (through the idempotent wrapper)
# ---------------------------------------------------------------------------

@router.post("/{merchant_id}/products", status_code=201)
def create_product(
    merchant_id: str, body: CreateProductBody, actor: MerchantActor, catalog: CatalogSvc
) -> ProductView:
    _require_roles(actor, _CATALOG_WRITE_ROLES)
    return catalog.create_product(
        CreateProductCommand(
            merchant_id=merchant_id,
            sku=body.sku,
            title=body.title,
            description=body.description,
            category=body.category,
            price=body.price,
            available_quantity=body.available_quantity,
            idempotency_key=body.idempotency_key,
        ),
        actor,
    )


@router.get("/{merchant_id}/products")
def list_products(
    merchant_id: str,
    actor: MerchantActor,
    catalog: CatalogSvc,
    cursor: str | None = None,
) -> ProductPage:
    return catalog.list_products(merchant_id, actor, cursor=cursor)


@router.get("/{merchant_id}/products/{product_id}")
def get_product(
    merchant_id: str, product_id: str, actor: MerchantActor, catalog: CatalogSvc
) -> ProductView:
    return catalog.get_product(product_id, actor)


@router.patch("/{merchant_id}/products/{product_id}")
def update_product(
    merchant_id: str,
    product_id: str,
    body: UpdateProductBody,
    actor: MerchantActor,
    catalog: CatalogSvc,
) -> ProductView:
    _require_roles(actor, _CATALOG_WRITE_ROLES)
    return catalog.update_product(
        UpdateProductCommand(
            merchant_id=merchant_id,
            product_id=product_id,
            expected_version=body.expected_version,
            idempotency_key=body.idempotency_key,
            title=body.title,
            description=body.description,
            category=body.category,
            price=body.price,
            available_quantity=body.available_quantity,
        ),
        actor,
    )


# ---------------------------------------------------------------------------
# AI-assisted draft extraction (D-010) — propose-only
# ---------------------------------------------------------------------------

@router.post("/{merchant_id}/products/extract-draft")
def extract_product_draft(
    merchant_id: str, body: ExtractDraftBody, actor: MerchantActor, extractor: Extractor
) -> dict[str, object]:
    """Propose-only AI extraction; nothing is persisted (D-010)."""
    _require_roles(actor, _CATALOG_WRITE_ROLES)
    draft = extractor.extract(body.text)
    return {
        "draft": draft.model_dump(),
        "persisted": False,
        "note": "Proposal only. Review and publish via the catalog; this endpoint never writes.",
    }


# ---------------------------------------------------------------------------
# Publication: dashboard-only confirmation issuance + verified actions
# ---------------------------------------------------------------------------

@router.post("/{merchant_id}/products/{product_id}/publication-confirmations")
def issue_publication_confirmation(
    merchant_id: str,
    product_id: str,
    body: IssueConfirmationBody,
    actor: MerchantActor,
    confirmations: ConfirmationSvc,
) -> dict[str, str]:
    """Dashboard-only confirmation issuance.

    MCP/AI credentials cannot mint tokens: issuance requires a merchant
    session; the merchant MCP adapter (C7) only *verifies* tokens.
    """
    _require_roles(actor, _CATALOG_WRITE_ROLES)
    token, expires_at, _jti = confirmations.issue(
        issuer_user_id=actor.actor_id,
        merchant_id=merchant_id,
        product_id=product_id,
        expected_version=body.expected_version,
        action=body.action,
    )
    return {"confirmation_token": token, "expires_at": expires_at.isoformat()}


def _verify_confirmation_for(
    confirmations: PublicationConfirmationService,
    *,
    token: str,
    action: str,
    merchant_id: str,
    product_id: str,
    expected_version: int,
    actor: ActorContext,
) -> PublicationConfirmationClaim:
    claim = confirmations.verify(token)
    mismatches = (
        (claim.action != action)
        or (claim.merchant_id != merchant_id)
        or (claim.product_id != product_id)
        or (claim.expected_version != expected_version)
        or (claim.issuer_user_id != actor.actor_id)
    )
    if mismatches:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "Publication confirmation does not match this request.",
            status_code=400,
        )
    return claim


@router.post("/{merchant_id}/products/{product_id}/publish")
def publish_product(
    merchant_id: str,
    product_id: str,
    body: PublicationActionBody,
    actor: MerchantActor,
    catalog: CatalogSvc,
    confirmations: ConfirmationSvc,
) -> ProductView:
    _require_roles(actor, _CATALOG_WRITE_ROLES)
    claim = _verify_confirmation_for(
        confirmations,
        token=body.confirmation_token,
        action=ACTION_PUBLISH,
        merchant_id=merchant_id,
        product_id=product_id,
        expected_version=body.expected_version,
        actor=actor,
    )
    result = catalog.publish_product(
        SetProductPublicationCommand(
            merchant_id=merchant_id,
            product_id=product_id,
            expected_version=body.expected_version,
            idempotency_key=body.idempotency_key,
        ),
        actor,
    )
    confirmations.mark_used(claim)
    return result


@router.post("/{merchant_id}/products/{product_id}/unpublish")
def unpublish_product(
    merchant_id: str,
    product_id: str,
    body: PublicationActionBody,
    actor: MerchantActor,
    catalog: CatalogSvc,
    confirmations: ConfirmationSvc,
) -> ProductView:
    _require_roles(actor, _CATALOG_WRITE_ROLES)
    claim = _verify_confirmation_for(
        confirmations,
        token=body.confirmation_token,
        action=ACTION_UNPUBLISH,
        merchant_id=merchant_id,
        product_id=product_id,
        expected_version=body.expected_version,
        actor=actor,
    )
    result = catalog.unpublish_product(
        SetProductPublicationCommand(
            merchant_id=merchant_id,
            product_id=product_id,
            expected_version=body.expected_version,
            idempotency_key=body.idempotency_key,
        ),
        actor,
    )
    confirmations.mark_used(claim)
    return result


# ---------------------------------------------------------------------------
# Policy and review queue
# ---------------------------------------------------------------------------

@router.get("/{merchant_id}/policy")
def get_policy(merchant_id: str, actor: MerchantActor, policy: PolicySvc) -> MerchantPolicyView:
    return policy.get_policy(merchant_id, actor)


@router.put("/{merchant_id}/policy")
def update_policy(
    merchant_id: str, body: UpdatePolicyBody, actor: MerchantActor, policy: PolicySvc
) -> MerchantPolicyView:
    return policy.update_policy(
        UpdateMerchantPolicyCommand(
            merchant_id=merchant_id,
            mode=body.mode,
            auto_accept_max=body.auto_accept_max,
            expected_version=body.expected_version,
            idempotency_key=body.idempotency_key,
        ),
        actor,
    )


@router.get("/{merchant_id}/reviews")
def list_reviews(
    merchant_id: str,
    actor: MerchantActor,
    policy: PolicySvc,
    cursor: str | None = None,
) -> MerchantReviewPage:
    return policy.list_reviews(merchant_id, actor, cursor=cursor)


# ---------------------------------------------------------------------------
# Transaction / audit read seams (owned by the transaction lane; 501 until 07)
# ---------------------------------------------------------------------------

def _transaction_not_wired() -> None:
    raise AppError(
        ErrorCode.INTERNAL_ERROR,
        "Transaction reads are wired at integration (07).",
        status_code=501,
    )


_TransactionSvc = Annotated[None, Depends(_transaction_not_wired)]


@router.get("/{merchant_id}/transactions")
def list_transactions(
    merchant_id: str,
    actor: MerchantActor,
    cursor: str | None = None,
    _svc: _TransactionSvc = None,
) -> None:
    """Will return the merchant's transactions via TransactionService."""


@router.get("/{merchant_id}/transactions/{transaction_id}")
def get_transaction(
    merchant_id: str,
    transaction_id: str,
    actor: MerchantActor,
    _svc: _TransactionSvc = None,
) -> None:
    """Will return a transaction status via TransactionService."""


@router.get("/{merchant_id}/transactions/{transaction_id}/audit")
def get_transaction_audit(
    merchant_id: str,
    transaction_id: str,
    actor: MerchantActor,
    cursor: str | None = None,
    _svc: _TransactionSvc = None,
) -> None:
    """Will return the audit trail via TransactionService."""
