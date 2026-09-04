from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class UpdatedTimestampMixin(TimestampMixin):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Merchant(Base, UpdatedTimestampMixin):
    __tablename__ = "merchants"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class MerchantUser(Base, TimestampMixin):
    __tablename__ = "merchant_users"
    __table_args__ = (UniqueConstraint("merchant_id", "user_id"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False, index=True)  # noqa: E501
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)


class Product(Base, UpdatedTimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("merchant_id", "sku"),
        CheckConstraint("price_minor >= 0", name="price_nonnegative"),
        CheckConstraint("available_quantity >= 0", name="stock_nonnegative"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False, index=True)  # noqa: E501
    sku: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(128))
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    available_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class ProductMetadata(Base):
    __tablename__ = "product_metadata"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), primary_key=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    attributes_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    search_text: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="MERCHANT")
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="APPROVED")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ProductImage(Base, TimestampMixin):
    __tablename__ = "product_images"
    __table_args__ = (
        UniqueConstraint("product_id", "sort_order"),
        UniqueConstraint("storage_path"),
        CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False, index=True)  # noqa: E501
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    public_url: Mapped[str | None] = mapped_column(String(2048))
    alt_text: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class MerchantPolicy(Base, UpdatedTimestampMixin):
    __tablename__ = "merchant_policies"
    __table_args__ = (
        UniqueConstraint("merchant_id", "version"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint(
            "auto_accept_max_minor IS NULL OR auto_accept_max_minor >= 0", name="limit_nonnegative"
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False, index=True)  # noqa: E501
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    auto_accept_max_minor: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str | None] = mapped_column(String(3))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class Buyer(Base, TimestampMixin):
    __tablename__ = "buyers"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    external_identity: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class PurchaseProposal(Base, TimestampMixin):
    __tablename__ = "purchase_proposals"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price_minor >= 0", name="unit_price_nonnegative"),
        CheckConstraint("total_minor >= 0", name="total_nonnegative"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyers.id"), nullable=False, index=True)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False, index=True)  # noqa: E501
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False)
    product_version: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    proposal_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PROPOSED")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BuyerAuthorization(Base, TimestampMixin):
    __tablename__ = "buyer_authorizations"
    __table_args__ = (
        CheckConstraint("max_quantity > 0", name="quantity_positive"),
        CheckConstraint("max_amount_minor >= 0", name="amount_nonnegative"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyers.id"), nullable=False, index=True)
    proposal_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_proposals.id"), nullable=False, index=True
    )
    proposal_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False)
    max_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    max_amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    authorized_by: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="REQUESTED")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MerchantDecision(Base, TimestampMixin):
    __tablename__ = "merchant_decisions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(
        ForeignKey("purchase_proposals.id"), nullable=False, index=True
    )
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False, index=True)  # noqa: E501
    policy_id: Mapped[str] = mapped_column(ForeignKey("merchant_policies.id"), nullable=False)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    decided_by: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Transaction(Base, UpdatedTimestampMixin):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("proposal_id"),
        CheckConstraint("amount_minor >= 0", name="amount_nonnegative"),
        CheckConstraint("length(currency) = 3", name="currency_length"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("purchase_proposals.id"), nullable=False)
    buyer_authorization_id: Mapped[str | None] = mapped_column(
        ForeignKey("buyer_authorizations.id")
    )
    merchant_decision_id: Mapped[str | None] = mapped_column(ForeignKey("merchant_decisions.id"))
    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id"), nullable=False, index=True)  # noqa: E501
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyers.id"), nullable=False, index=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="PROPOSED")


class IdempotencyRecord(Base, TimestampMixin):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("actor_id", "operation", "idempotency_key"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    operation: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    response_code: Mapped[int | None] = mapped_column(Integer)
    response_body_hash: Mapped[str | None] = mapped_column(String(128))


class PaymentAttempt(Base, UpdatedTimestampMixin):
    __tablename__ = "payment_attempts"
    __table_args__ = (
        UniqueConstraint("transaction_id", "attempt_number"),
        UniqueConstraint("provider", "provider_order_id"),
        CheckConstraint("attempt_number > 0", name="attempt_positive"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.id"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_request_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_order_id: Mapped[str | None] = mapped_column(String(255))
    provider_payment_id: Mapped[str | None] = mapped_column(String(255))
    provider_order_state: Mapped[str | None] = mapped_column(String(64))
    provider_payment_state: Mapped[str | None] = mapped_column(String(64))
    capture_state: Mapped[str | None] = mapped_column(String(64))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProviderWebhook(Base):
    __tablename__ = "provider_webhooks"
    __table_args__ = (UniqueConstraint("provider", "provider_event_id"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    signature_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(ForeignKey("transactions.id"), index=True)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TransactionEvent(Base, TimestampMixin):
    __tablename__ = "transaction_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(255))
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    previous_state: Mapped[str | None] = mapped_column(String(40))
    new_state: Mapped[str | None] = mapped_column(String(40))
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    provider_reference_redacted: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


Index("ix_products_merchant_status", Product.merchant_id, Product.status)
Index("ix_transactions_merchant_state", Transaction.merchant_id, Transaction.state)
