"""Merchant policy application service.

Owns purchase policy persistence, configuration, versioning, and manual-review queue operations.
Transaction policy evaluation is owned by Transaction Core (B2).
"""

from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_commerce_gateway.application.catalog_service import _require_merchant_access
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    BuyerAuthorizationView,
    EvaluateMerchantPolicyCommand,
    MerchantDecisionView,
    MerchantPolicyView,
    MerchantReviewItem,
    MerchantReviewPage,
    Money,
    PurchaseProposalView,
    RecordMerchantDecisionCommand,
    UpdateMerchantPolicyCommand,
)
from ai_commerce_gateway.contracts.services import MerchantPolicyService
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.core.ids import new_id
from ai_commerce_gateway.domain.enums import (
    AuthorizationStatus,
    MerchantDecisionValue,
    MerchantRole,
    NextRequiredGate,
    ProposalStatus,
    RecordStatus,
)
from ai_commerce_gateway.domain.policy import MerchantPolicyEntity
from ai_commerce_gateway.domain.product import MoneyMinor
from ai_commerce_gateway.domain.repositories import MerchantPolicyRepository
from ai_commerce_gateway.infrastructure.database import models as orm


def _to_policy_view(entity: MerchantPolicyEntity) -> MerchantPolicyView:
    return MerchantPolicyView(
        id=entity.id,
        merchant_id=entity.merchant_id,
        mode=entity.mode,
        auto_accept_max=(
            Money(
                amount_minor=entity.auto_accept_max.amount_minor,
                currency=entity.auto_accept_max.currency,
            )
            if entity.auto_accept_max is not None
            else None
        ),
        version=entity.version,
    )


class ApplicationMerchantPolicyService(MerchantPolicyService):
    def __init__(
        self,
        policy_repo: MerchantPolicyRepository,
        session: Session | None = None,
    ) -> None:
        self._policy_repo = policy_repo
        self._session = session

    def get_policy(self, merchant_id: str, actor: ActorContext) -> MerchantPolicyView:
        _require_merchant_access(actor, merchant_id)
        policy = self._policy_repo.get_active(merchant_id)
        if policy is None:
            raise AppError(
                ErrorCode.NOT_FOUND,
                "Policy not found for this merchant.",
                status_code=404,
            )
        return _to_policy_view(policy)

    def update_policy(
        self, command: UpdateMerchantPolicyCommand, actor: ActorContext
    ) -> MerchantPolicyView:
        _require_merchant_access(
            actor, command.merchant_id, required_roles=frozenset([MerchantRole.ADMIN])
        )

        current = self._policy_repo.get_active(command.merchant_id)
        now = datetime.now(tz=UTC)

        auto_accept_max_minor = (
            MoneyMinor(
                amount_minor=command.auto_accept_max.amount_minor,
                currency=command.auto_accept_max.currency,
            )
            if command.auto_accept_max is not None
            else None
        )

        if current is None:
            if command.expected_version is not None and command.expected_version != 1:
                raise AppError(
                    ErrorCode.VALIDATION_ERROR,
                    "Policy does not exist yet; expected version mismatch.",
                    status_code=409,
                )
            new_policy = MerchantPolicyEntity(
                id=new_id("pol"),
                merchant_id=command.merchant_id,
                mode=command.mode,
                auto_accept_max=auto_accept_max_minor,
                version=1,
                status=RecordStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
            saved = self._policy_repo.add(new_policy)
            return _to_policy_view(saved)

        if (
            command.expected_version is not None
            and current.version != command.expected_version
        ):
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "Version mismatch (stale write).",
                status_code=409,
            )

        updated_policy = replace(
            current,
            mode=command.mode,
            auto_accept_max=auto_accept_max_minor,
            version=current.version + 1,
            updated_at=now,
        )
        saved = self._policy_repo.update(updated_policy)
        return _to_policy_view(saved)

    def list_reviews(
        self, merchant_id: str, actor: ActorContext, cursor: str | None = None
    ) -> MerchantReviewPage:
        _require_merchant_access(actor, merchant_id)
        if self._session is None:
            return MerchantReviewPage(items=(), next_cursor=None)

        limit = 50
        stmt = (
            select(orm.MerchantDecision, orm.PurchaseProposal, orm.BuyerAuthorization)
            .join(
                orm.PurchaseProposal,
                orm.MerchantDecision.proposal_id == orm.PurchaseProposal.id,
            )
            .join(
                orm.BuyerAuthorization,
                orm.BuyerAuthorization.proposal_id == orm.PurchaseProposal.id,
            )
            .where(
                orm.MerchantDecision.merchant_id == merchant_id,
                orm.MerchantDecision.decision
                == MerchantDecisionValue.REVIEW_REQUIRED.value,
            )
            .order_by(orm.MerchantDecision.created_at, orm.MerchantDecision.id)
            .limit(limit)
        )
        if cursor is not None:
            cursor_row = self._session.get(orm.MerchantDecision, cursor)
            if cursor_row:
                stmt = stmt.where(
                    (orm.MerchantDecision.created_at > cursor_row.created_at)
                    | (
                        (orm.MerchantDecision.created_at == cursor_row.created_at)
                        & (orm.MerchantDecision.id > cursor)
                    )
                )

        results = self._session.execute(stmt).all()
        items = []
        for dec_row, prop_row, auth_row in results:
            prop_view = PurchaseProposalView(
                id=prop_row.id,
                buyer_id=prop_row.buyer_id,
                merchant_id=prop_row.merchant_id,
                product_id=prop_row.product_id,
                product_version=prop_row.product_version,
                quantity=prop_row.quantity,
                unit_price=Money(
                    amount_minor=prop_row.unit_price_minor,
                    currency=prop_row.currency,
                ),
                total=Money(
                    amount_minor=prop_row.total_minor,
                    currency=prop_row.currency,
                ),
                proposal_hash=prop_row.proposal_hash,
                status=ProposalStatus(prop_row.status),
                next_required_gate=NextRequiredGate.MERCHANT_REVIEW_REQUIRED,
                expires_at=prop_row.expires_at,
                created_at=prop_row.created_at,
            )
            auth_view = BuyerAuthorizationView(
                id=auth_row.id,
                buyer_id=auth_row.buyer_id,
                proposal_id=auth_row.proposal_id,
                proposal_hash=auth_row.proposal_hash,
                merchant_id=auth_row.merchant_id,
                product_id=auth_row.product_id,
                max_quantity=auth_row.max_quantity,
                max_amount=Money(
                    amount_minor=auth_row.max_amount_minor,
                    currency=auth_row.currency,
                ),
                authorized_by=auth_row.authorized_by,
                status=AuthorizationStatus(auth_row.status),
                expires_at=auth_row.expires_at,
                created_at=auth_row.created_at,
            )
            items.append(
                MerchantReviewItem(
                    proposal=prop_view,
                    authorization=auth_view,
                    review_reason=dec_row.reason_code,
                )
            )

        next_cursor = (
            results[-1][0].id if len(results) == limit else None
        )
        return MerchantReviewPage(items=tuple(items), next_cursor=next_cursor)

    def evaluate(
        self, command: EvaluateMerchantPolicyCommand, actor: ActorContext
    ) -> MerchantDecisionView:
        raise NotImplementedError(
            "Transaction policy evaluation is owned by Transaction Core (B2)."
        )

    def record_manual_decision(
        self, command: RecordMerchantDecisionCommand, actor: ActorContext
    ) -> MerchantDecisionView:
        raise NotImplementedError(
            "Proposal manual decision recording is owned by Transaction Core (B2)."
        )
