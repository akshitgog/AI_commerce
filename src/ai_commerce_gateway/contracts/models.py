from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_commerce_gateway.core.errors import ErrorCode
from ai_commerce_gateway.domain.enums import (
    ActorType,
    AuthorizationStatus,
    MerchantDecisionValue,
    MerchantRole,
    NextRequiredGate,
    PolicyMode,
    ProductStatus,
    ProposalStatus,
    ProviderName,
    TransactionState,
)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Money(ContractModel):
    """Trusted money: integer minor units plus explicit uppercase ISO currency.

    Strictly rejects bools, floats (incl. NaN/Infinity), numeric strings and
    any implicit/loose currency representation (P0-3).
    """

    amount_minor: int = Field(ge=0, strict=True)
    currency: str = Field(pattern=r"^[A-Z]{3}$", strict=True)


class ErrorBody(ContractModel):
    code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(ContractModel):
    error: ErrorBody
    correlation_id: str


class ActorContext(ContractModel):
    actor_id: str
    actor_type: ActorType
    merchant_ids: frozenset[str] = frozenset()
    roles: frozenset[MerchantRole] = frozenset()
    correlation_id: str


class MerchantView(ContractModel):
    id: str
    name: str
    status: str


class CreateMerchantCommand(ContractModel):
    name: str = Field(min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=1, max_length=255)


class ProductImageView(ContractModel):
    id: str
    url: str
    alt_text: str | None = None
    sort_order: int = Field(ge=0, strict=True)


class ProductView(ContractModel):
    id: str
    merchant_id: str
    sku: str
    title: str
    description: str
    category: str | None = None
    price: Money
    available_quantity: int = Field(ge=0, strict=True)
    status: ProductStatus
    version: int = Field(ge=1, strict=True)
    images: tuple[ProductImageView, ...] = ()


class CreateProductCommand(ContractModel):
    merchant_id: str
    sku: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=255)
    description: str
    category: str | None = None
    price: Money
    available_quantity: int = Field(ge=0, strict=True)
    idempotency_key: str = Field(min_length=1, max_length=255)


class UpdateProductCommand(ContractModel):
    merchant_id: str
    product_id: str
    expected_version: int = Field(ge=1, strict=True)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = None
    price: Money | None = None
    available_quantity: int | None = Field(default=None, ge=0, strict=True)
    idempotency_key: str = Field(min_length=1, max_length=255)


class SetProductPublicationCommand(ContractModel):
    merchant_id: str
    product_id: str
    expected_version: int = Field(ge=1, strict=True)
    idempotency_key: str = Field(min_length=1, max_length=255)


class AddProductImageCommand(ContractModel):
    merchant_id: str
    product_id: str
    filename: str
    content_type: str
    content: bytes
    alt_text: str | None = Field(default=None, max_length=500)
    sort_order: int = Field(ge=0, le=2, strict=True)
    idempotency_key: str = Field(min_length=1, max_length=255)


class DeleteProductImageCommand(ContractModel):
    merchant_id: str
    product_id: str
    image_id: str
    idempotency_key: str = Field(min_length=1, max_length=255)


class CatalogSearchQuery(ContractModel):
    merchant_id: str
    query: str | None = None
    category: str | None = None
    min_price_minor: int | None = Field(default=None, ge=0, strict=True)
    max_price_minor: int | None = Field(default=None, ge=0, strict=True)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100, strict=True)

    @model_validator(mode="after")
    def validate_price_range(self) -> "CatalogSearchQuery":
        if (
            self.min_price_minor is not None
            and self.max_price_minor is not None
            and self.min_price_minor > self.max_price_minor
        ):
            raise ValueError("min_price_minor cannot exceed max_price_minor")
        return self


class CatalogSearchResult(ContractModel):
    items: tuple[ProductView, ...]
    next_cursor: str | None = None


class ProductPage(ContractModel):
    items: tuple[ProductView, ...]
    next_cursor: str | None = None


class CreateProposalCommand(ContractModel):
    merchant_id: str
    product_id: str
    quantity: int = Field(ge=1, strict=True)
    idempotency_key: str = Field(min_length=1, max_length=255)


class PurchaseProposalView(ContractModel):
    id: str
    buyer_id: str
    merchant_id: str
    product_id: str
    product_version: int
    quantity: int
    unit_price: Money
    total: Money
    proposal_hash: str
    status: ProposalStatus
    next_required_gate: NextRequiredGate
    expires_at: datetime
    created_at: datetime


class RequestAuthorizationCommand(ContractModel):
    proposal_id: str
    idempotency_key: str = Field(min_length=1, max_length=255)


class ApproveAuthorizationCommand(ContractModel):
    proposal_id: str
    proposal_hash: str
    max_quantity: int = Field(ge=1, strict=True)
    max_amount: Money
    expires_at: datetime
    idempotency_key: str = Field(min_length=1, max_length=255)


class BuyerAuthorizationView(ContractModel):
    id: str
    buyer_id: str
    proposal_id: str
    proposal_hash: str
    merchant_id: str
    product_id: str
    max_quantity: int
    max_amount: Money
    authorized_by: str | None
    status: AuthorizationStatus
    expires_at: datetime
    created_at: datetime


class EvaluateMerchantPolicyCommand(ContractModel):
    proposal_id: str


class RecordMerchantDecisionCommand(ContractModel):
    proposal_id: str
    decision: MerchantDecisionValue
    reason_code: str
    expires_at: datetime | None = None
    idempotency_key: str = Field(min_length=1, max_length=255)


class MerchantPolicyView(ContractModel):
    id: str
    merchant_id: str
    mode: PolicyMode
    auto_accept_max: Money | None = None
    version: int = Field(strict=True)


class UpdateMerchantPolicyCommand(ContractModel):
    merchant_id: str
    mode: PolicyMode
    auto_accept_max: Money | None = None
    expected_version: int | None = Field(default=None, ge=1, strict=True)
    idempotency_key: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def validate_limit(self) -> "UpdateMerchantPolicyCommand":
        if self.mode is PolicyMode.AUTO_BELOW_LIMIT and self.auto_accept_max is None:
            raise ValueError("AUTO_BELOW_LIMIT requires auto_accept_max")
        if self.mode is not PolicyMode.AUTO_BELOW_LIMIT and self.auto_accept_max is not None:
            raise ValueError("auto_accept_max is valid only for AUTO_BELOW_LIMIT")
        return self


class MerchantDecisionView(ContractModel):
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


class MerchantReviewItem(ContractModel):
    proposal: PurchaseProposalView
    authorization: BuyerAuthorizationView
    review_reason: str


class MerchantReviewPage(ContractModel):
    items: tuple[MerchantReviewItem, ...]
    next_cursor: str | None = None


class CreateTransactionCommand(ContractModel):
    proposal_id: str
    idempotency_key: str = Field(min_length=1, max_length=255)


class ExecuteTransactionCommand(ContractModel):
    transaction_id: str
    idempotency_key: str = Field(min_length=1, max_length=255)


class ReconcileTransactionCommand(ContractModel):
    transaction_id: str
    idempotency_key: str = Field(min_length=1, max_length=255)


class ProviderPhase(ContractModel):
    provider: ProviderName
    order_state: str | None = None
    payment_state: str | None = None
    capture_state: str | None = None
    last_verified_at: datetime | None = None


class TransactionView(ContractModel):
    id: str
    proposal_id: str
    merchant_id: str
    buyer_id: str
    amount: Money
    state: TransactionState
    provider_phase: ProviderPhase | None = None
    created_at: datetime
    updated_at: datetime


class TransactionEventView(ContractModel):
    id: str
    transaction_id: str
    event_type: str
    actor_type: ActorType
    actor_id: str | None
    reason_code: str
    previous_state: TransactionState | None
    new_state: TransactionState | None
    correlation_id: str
    provider_reference_redacted: str | None
    metadata: dict[str, Any]
    created_at: datetime


class AuditPage(ContractModel):
    items: tuple[TransactionEventView, ...]
    next_cursor: str | None = None


class TransactionPage(ContractModel):
    items: tuple[TransactionView, ...]
    next_cursor: str | None = None


class CreateProviderOrderCommand(ContractModel):
    transaction_id: str
    attempt_id: str
    amount: Money
    receipt: str
    request_fingerprint: str


class VerifyCheckoutCommand(ContractModel):
    transaction_id: str
    provider_order_id: str
    provider_payment_id: str
    signature: str


class HandleWebhookCommand(ContractModel):
    raw_body: bytes
    signature: str


class ProviderLookupCommand(ContractModel):
    provider_order_id: str | None = None
    provider_payment_id: str | None = None


class ProviderObservation(ContractModel):
    provider: ProviderName
    provider_order_id: str | None = None
    provider_payment_id: str | None = None
    provider_order_state: str | None = None
    provider_payment_state: str | None = None
    capture_state: str | None = None
    authenticity_verified: bool
    observed_at: datetime
    observation_source: str


class StoredImage(ContractModel):
    storage_path: str
    public_url: str | None = None
