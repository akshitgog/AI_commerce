import hashlib
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Final

from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import (
    AuthorizationStatus,
    MerchantDecisionValue,
    NextRequiredGate,
    PolicyMode,
    ProductStatus,
    ProposalStatus,
)

PROPOSAL_HASH_PREFIX: Final = "sha256:"


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")


def _validate_money(amount_minor: int, currency: str) -> None:
    if isinstance(amount_minor, bool) or not isinstance(amount_minor, int):
        raise TypeError("money must use integer minor units")
    if amount_minor < 0:
        raise ValueError("money must be non-negative")
    if (
        len(currency) != 3
        or not currency.isascii()
        or not currency.isalpha()
        or not currency.isupper()
    ):
        raise ValueError("currency must be a three-letter uppercase code")


def _authorization_invalid(reason: str) -> AppError:
    return AppError(
        ErrorCode.AUTHORIZATION_INVALID,
        "Buyer authorization does not match the proposal.",
        status_code=409,
        details={"reason": reason},
    )


@dataclass(frozen=True, slots=True)
class TrustedProductSnapshot:
    id: str
    merchant_id: str
    version: int
    price_minor: int
    currency: str
    available_quantity: int
    status: ProductStatus

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("product version must be positive")
        _validate_money(self.price_minor, self.currency)
        if self.available_quantity < 0:
            raise ValueError("available quantity must be non-negative")


@dataclass(frozen=True, slots=True)
class PurchaseProposal:
    id: str
    buyer_id: str
    merchant_id: str
    product_id: str
    product_version: int
    quantity: int
    unit_price_minor: int
    total_minor: int
    currency: str
    proposal_hash: str
    status: ProposalStatus
    expires_at: datetime
    created_at: datetime

    def __post_init__(self) -> None:
        if self.quantity < 1:
            raise ValueError("quantity must be positive")
        if self.product_version < 1:
            raise ValueError("product version must be positive")
        _validate_money(self.unit_price_minor, self.currency)
        _validate_money(self.total_minor, self.currency)
        if self.total_minor != self.unit_price_minor * self.quantity:
            raise ValueError("proposal total must equal trusted unit price times quantity")
        _require_utc(self.created_at, "created_at")
        _require_utc(self.expires_at, "expires_at")
        if self.expires_at <= self.created_at:
            raise ValueError("proposal expiry must be after creation")
        expected_hash = proposal_hash_for(
            buyer_id=self.buyer_id,
            merchant_id=self.merchant_id,
            product_id=self.product_id,
            product_version=self.product_version,
            quantity=self.quantity,
            unit_price_minor=self.unit_price_minor,
            total_minor=self.total_minor,
            currency=self.currency,
            expires_at=self.expires_at,
        )
        if self.proposal_hash != expected_hash:
            raise ValueError("proposal hash does not match its immutable commercial snapshot")

    def require_active(self, now: datetime) -> None:
        _require_utc(now, "now")
        if self.status is not ProposalStatus.PROPOSED or now >= self.expires_at:
            raise AppError(
                ErrorCode.PROPOSAL_STALE,
                "Purchase proposal is no longer active.",
                status_code=409,
                details={"proposal_id": self.id},
            )


def proposal_hash_for(
    *,
    buyer_id: str,
    merchant_id: str,
    product_id: str,
    product_version: int,
    quantity: int,
    unit_price_minor: int,
    total_minor: int,
    currency: str,
    expires_at: datetime,
) -> str:
    _require_utc(expires_at, "expires_at")
    canonical_snapshot = {
        "buyer_id": buyer_id,
        "currency": currency,
        "expires_at": expires_at.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "merchant_id": merchant_id,
        "product_id": product_id,
        "product_version": product_version,
        "quantity": quantity,
        "total_minor": total_minor,
        "unit_price_minor": unit_price_minor,
    }
    encoded = json.dumps(canonical_snapshot, sort_keys=True, separators=(",", ":")).encode()
    return f"{PROPOSAL_HASH_PREFIX}{hashlib.sha256(encoded).hexdigest()}"


def create_purchase_proposal(
    *,
    proposal_id: str,
    buyer_id: str,
    requested_merchant_id: str,
    product: TrustedProductSnapshot,
    quantity: int,
    created_at: datetime,
    expires_at: datetime,
) -> PurchaseProposal:
    if product.merchant_id != requested_merchant_id:
        raise AppError(
            ErrorCode.NOT_FOUND,
            "Published product was not found for this merchant.",
            status_code=404,
        )
    if product.status is not ProductStatus.PUBLISHED:
        raise AppError(
            ErrorCode.PRODUCT_UNAVAILABLE,
            "Product is not published.",
            status_code=409,
        )
    if quantity < 1 or quantity > product.available_quantity:
        raise AppError(
            ErrorCode.PRODUCT_UNAVAILABLE,
            "Requested quantity is unavailable.",
            status_code=409,
            details={"available_quantity": product.available_quantity},
        )
    total_minor = product.price_minor * quantity
    proposal_hash = proposal_hash_for(
        buyer_id=buyer_id,
        merchant_id=product.merchant_id,
        product_id=product.id,
        product_version=product.version,
        quantity=quantity,
        unit_price_minor=product.price_minor,
        total_minor=total_minor,
        currency=product.currency,
        expires_at=expires_at,
    )
    return PurchaseProposal(
        id=proposal_id,
        buyer_id=buyer_id,
        merchant_id=product.merchant_id,
        product_id=product.id,
        product_version=product.version,
        quantity=quantity,
        unit_price_minor=product.price_minor,
        total_minor=total_minor,
        currency=product.currency,
        proposal_hash=proposal_hash,
        status=ProposalStatus.PROPOSED,
        expires_at=expires_at,
        created_at=created_at,
    )


@dataclass(frozen=True, slots=True)
class BuyerAuthorization:
    id: str
    buyer_id: str
    proposal_id: str
    proposal_hash: str
    merchant_id: str
    product_id: str
    max_quantity: int
    max_amount_minor: int
    currency: str
    authorized_by: str | None
    status: AuthorizationStatus
    expires_at: datetime
    created_at: datetime

    def __post_init__(self) -> None:
        if self.max_quantity < 1:
            raise ValueError("authorization quantity must be positive")
        _validate_money(self.max_amount_minor, self.currency)
        _require_utc(self.created_at, "created_at")
        _require_utc(self.expires_at, "expires_at")

    def approve(
        self,
        proposal: PurchaseProposal,
        *,
        proposal_hash: str,
        max_quantity: int,
        max_amount_minor: int,
        currency: str,
        expires_at: datetime,
        authorized_by: str,
        now: datetime,
    ) -> "BuyerAuthorization":
        proposal.require_active(now)
        if self.status is not AuthorizationStatus.REQUESTED:
            raise _authorization_invalid("authorization_not_requested")
        if proposal_hash != proposal.proposal_hash:
            raise _authorization_invalid("proposal_hash_mismatch")
        if max_quantity != proposal.quantity:
            raise _authorization_invalid("quantity_mismatch")
        if max_amount_minor != proposal.total_minor:
            raise _authorization_invalid("amount_mismatch")
        if currency != proposal.currency:
            raise _authorization_invalid("currency_mismatch")
        _require_utc(expires_at, "expires_at")
        if expires_at <= now or expires_at > proposal.expires_at:
            raise _authorization_invalid("expiry_out_of_scope")
        if not authorized_by.strip():
            raise _authorization_invalid("human_approver_missing")
        return replace(
            self,
            proposal_hash=proposal_hash,
            max_quantity=max_quantity,
            max_amount_minor=max_amount_minor,
            currency=currency,
            authorized_by=authorized_by,
            status=AuthorizationStatus.APPROVED,
            expires_at=expires_at,
        )

    def require_matches(self, proposal: PurchaseProposal, *, now: datetime) -> None:
        proposal.require_active(now)
        checks = {
            "authorization_not_approved": self.status is not AuthorizationStatus.APPROVED,
            "authorization_expired": now >= self.expires_at,
            "buyer_mismatch": self.buyer_id != proposal.buyer_id,
            "proposal_mismatch": self.proposal_id != proposal.id,
            "proposal_hash_mismatch": self.proposal_hash != proposal.proposal_hash,
            "merchant_mismatch": self.merchant_id != proposal.merchant_id,
            "product_mismatch": self.product_id != proposal.product_id,
            "quantity_mismatch": self.max_quantity != proposal.quantity,
            "amount_mismatch": self.max_amount_minor != proposal.total_minor,
            "currency_mismatch": self.currency != proposal.currency,
        }
        for reason, failed in checks.items():
            if failed:
                raise _authorization_invalid(reason)


def request_buyer_authorization(
    *, authorization_id: str, proposal: PurchaseProposal, requested_at: datetime
) -> BuyerAuthorization:
    proposal.require_active(requested_at)
    return BuyerAuthorization(
        id=authorization_id,
        buyer_id=proposal.buyer_id,
        proposal_id=proposal.id,
        proposal_hash=proposal.proposal_hash,
        merchant_id=proposal.merchant_id,
        product_id=proposal.product_id,
        max_quantity=proposal.quantity,
        max_amount_minor=proposal.total_minor,
        currency=proposal.currency,
        authorized_by=None,
        status=AuthorizationStatus.REQUESTED,
        expires_at=proposal.expires_at,
        created_at=requested_at,
    )


@dataclass(frozen=True, slots=True)
class MerchantPolicySnapshot:
    id: str
    merchant_id: str
    mode: PolicyMode
    auto_accept_max_minor: int | None
    currency: str | None
    version: int

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("policy version must be positive")
        if self.mode is PolicyMode.AUTO_BELOW_LIMIT:
            if self.auto_accept_max_minor is None or self.currency is None:
                raise ValueError("AUTO_BELOW_LIMIT requires money limit")
            _validate_money(self.auto_accept_max_minor, self.currency)
        elif self.auto_accept_max_minor is not None or self.currency is not None:
            raise ValueError("non-limit policy cannot include a money limit")


@dataclass(frozen=True, slots=True)
class MerchantDecision:
    id: str
    proposal_id: str
    merchant_id: str
    policy_id: str
    policy_version: int
    decision: MerchantDecisionValue
    reason_code: str
    decided_by: str
    expires_at: datetime | None
    created_at: datetime

    def require_matches(self, proposal: PurchaseProposal, *, now: datetime) -> None:
        if self.proposal_id != proposal.id:
            raise AppError(ErrorCode.POLICY_DENIED, "Merchant decision is for another proposal.")
        if self.merchant_id != proposal.merchant_id:
            raise AppError(ErrorCode.POLICY_DENIED, "Merchant decision is for another merchant.")
        if self.expires_at is not None and now >= self.expires_at:
            raise AppError(ErrorCode.POLICY_DENIED, "Merchant decision has expired.")

    def is_current_for(self, policy: MerchantPolicySnapshot) -> bool:
        return self.policy_id == policy.id and self.policy_version == policy.version


def evaluate_merchant_policy(
    *,
    decision_id: str,
    proposal: PurchaseProposal,
    policy: MerchantPolicySnapshot,
    decided_at: datetime,
) -> MerchantDecision:
    proposal.require_active(decided_at)
    if policy.merchant_id != proposal.merchant_id:
        raise AppError(
            ErrorCode.FORBIDDEN, "Merchant policy does not own this proposal.", status_code=403
        )

    if policy.mode is PolicyMode.DENY_ALL:
        decision = MerchantDecisionValue.DENY
        reason_code = "POLICY_DENY_ALL"
    elif policy.mode is PolicyMode.MANUAL_ALL:
        decision = MerchantDecisionValue.REVIEW_REQUIRED
        reason_code = "POLICY_MANUAL_REVIEW"
    elif (
        policy.currency == proposal.currency
        and policy.auto_accept_max_minor is not None
        and proposal.total_minor <= policy.auto_accept_max_minor
    ):
        decision = MerchantDecisionValue.ALLOW
        reason_code = "POLICY_AUTO_ALLOWED"
    else:
        decision = MerchantDecisionValue.REVIEW_REQUIRED
        reason_code = "POLICY_LIMIT_REVIEW"

    return MerchantDecision(
        id=decision_id,
        proposal_id=proposal.id,
        merchant_id=proposal.merchant_id,
        policy_id=policy.id,
        policy_version=policy.version,
        decision=decision,
        reason_code=reason_code,
        decided_by=f"policy:{policy.id}:v{policy.version}",
        expires_at=proposal.expires_at,
        created_at=decided_at,
    )


def record_manual_merchant_decision(
    *,
    decision_id: str,
    proposal: PurchaseProposal,
    review_decision: MerchantDecision,
    decision: MerchantDecisionValue,
    reason_code: str,
    decided_by: str,
    expires_at: datetime | None,
    decided_at: datetime,
) -> MerchantDecision:
    proposal.require_active(decided_at)
    review_decision.require_matches(proposal, now=decided_at)
    if review_decision.decision is not MerchantDecisionValue.REVIEW_REQUIRED:
        raise AppError(
            ErrorCode.INVALID_STATE,
            "Proposal is not awaiting merchant review.",
            status_code=409,
        )
    if decision not in {MerchantDecisionValue.ALLOW, MerchantDecisionValue.DENY}:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "Manual decision must allow or deny the proposal.",
            status_code=422,
        )
    if not reason_code.strip() or not decided_by.strip():
        raise AppError(ErrorCode.VALIDATION_ERROR, "Manual decision requires actor and reason.")
    effective_expiry = expires_at or proposal.expires_at
    _require_utc(effective_expiry, "expires_at")
    if effective_expiry <= decided_at or effective_expiry > proposal.expires_at:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "Manual decision expiry exceeds the proposal scope.",
            status_code=422,
        )
    return MerchantDecision(
        id=decision_id,
        proposal_id=proposal.id,
        merchant_id=proposal.merchant_id,
        policy_id=review_decision.policy_id,
        policy_version=review_decision.policy_version,
        decision=decision,
        reason_code=reason_code,
        decided_by=decided_by,
        expires_at=effective_expiry,
        created_at=decided_at,
    )


def determine_next_gate(
    proposal: PurchaseProposal,
    authorization: BuyerAuthorization | None,
    merchant_decision: MerchantDecision | None,
    *,
    now: datetime,
) -> NextRequiredGate:
    proposal.require_active(now)
    if (
        authorization is None
        or authorization.status is not AuthorizationStatus.APPROVED
        or now >= authorization.expires_at
    ):
        return NextRequiredGate.BUYER_AUTH_REQUIRED
    authorization.require_matches(proposal, now=now)
    if merchant_decision is None or (
        merchant_decision.expires_at is not None and now >= merchant_decision.expires_at
    ):
        return NextRequiredGate.MERCHANT_POLICY_PENDING
    merchant_decision.require_matches(proposal, now=now)
    if merchant_decision.decision is MerchantDecisionValue.REVIEW_REQUIRED:
        return NextRequiredGate.MERCHANT_REVIEW_REQUIRED
    if merchant_decision.decision is MerchantDecisionValue.DENY:
        raise AppError(
            ErrorCode.POLICY_DENIED,
            "Merchant policy denied the proposal.",
            status_code=409,
            details={"reason_code": merchant_decision.reason_code},
        )
    return NextRequiredGate.READY


def require_current_product(proposal: PurchaseProposal, product: TrustedProductSnapshot) -> None:
    mismatches = {
        "merchant": product.merchant_id != proposal.merchant_id,
        "product": product.id != proposal.product_id,
        "version": product.version != proposal.product_version,
        "unit_price": product.price_minor != proposal.unit_price_minor,
        "currency": product.currency != proposal.currency,
        "stock": product.available_quantity < proposal.quantity,
        "publication": product.status is not ProductStatus.PUBLISHED,
    }
    failed = [name for name, mismatch in mismatches.items() if mismatch]
    if failed:
        raise AppError(
            ErrorCode.PROPOSAL_STALE,
            "Current product state no longer matches the proposal.",
            status_code=409,
            details={"mismatches": failed},
        )
