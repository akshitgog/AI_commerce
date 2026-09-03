from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_commerce_gateway.domain.enums import (
    AuthorizationStatus,
    MerchantDecisionValue,
    PolicyMode,
    ProductStatus,
    ProposalStatus,
    ProviderName,
    TransactionState,
)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Money(ContractModel):
    amount_minor: int = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class ActorContext(ContractModel):
    actor_id: str
    actor_type: str
    merchant_ids: frozenset[str] = frozenset()
    roles: frozenset[str] = frozenset()
    correlation_id: str


class ProductImageView(ContractModel):
    id: str
    url: str
    alt_text: str | None = None
    sort_order: int = Field(ge=0)


class ProductView(ContractModel):
    id: str
    merchant_id: str
    sku: str
    title: str
    description: str
    category: str | None = None
    price: Money
    available_quantity: int = Field(ge=0)
    status: ProductStatus
    version: int = Field(ge=1)
    images: tuple[ProductImageView, ...] = ()


class CatalogSearchQuery(ContractModel):
    merchant_id: str
    query: str | None = None
    category: str | None = None
    min_price_minor: int | None = Field(default=None, ge=0)
    max_price_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    cursor: str | None = None
    limit: int = Field(default=20, ge=1, le=100)

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


class CreateProposalCommand(ContractModel):
    merchant_id: str
    product_id: str
    quantity: int = Field(ge=1)
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
    expires_at: datetime
    created_at: datetime


class RequestAuthorizationCommand(ContractModel):
    proposal_id: str
    idempotency_key: str = Field(min_length=1, max_length=255)


class ApproveAuthorizationCommand(ContractModel):
    proposal_id: str
    proposal_hash: str
    max_quantity: int = Field(ge=1)
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
    version: int


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
    actor_type: str
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


class ProviderEvidence(ContractModel):
    provider: ProviderName
    provider_order_id: str | None = None
    provider_payment_id: str | None = None
    provider_order_state: str | None = None
    provider_payment_state: str | None = None
    capture_state: str | None = None
    verified: bool = False
    observed_at: datetime
    evidence_source: str


class StoredImage(ContractModel):
    storage_path: str
    public_url: str | None = None
