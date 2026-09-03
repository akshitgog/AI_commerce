from ai_commerce_gateway.contracts.models import (
    ActorContext,
    AddProductImageCommand,
    ApproveAuthorizationCommand,
    CreateProductCommand,
    ErrorEnvelope,
    ProductView,
    PurchaseProposalView,
    TransactionView,
)
from ai_commerce_gateway.core.errors import ErrorCode
from ai_commerce_gateway.core.ids import EntityPrefix
from ai_commerce_gateway.domain.enums import (
    ActorType,
    AuthorizationStatus,
    MerchantDecisionValue,
    MerchantRole,
    NextRequiredGate,
    PolicyMode,
    ProductStatus,
    TransactionState,
)


def field_names(model: type) -> set[str]:
    return set(model.model_fields)


def enum_values(enum: type) -> set[str]:
    return {member.value for member in enum}


def test_cross_lane_dto_shapes_are_frozen() -> None:
    assert field_names(ActorContext) == {
        "actor_id",
        "actor_type",
        "merchant_ids",
        "roles",
        "correlation_id",
    }
    assert field_names(ProductView) == {
        "id",
        "merchant_id",
        "sku",
        "title",
        "description",
        "category",
        "price",
        "available_quantity",
        "status",
        "version",
        "images",
    }
    assert field_names(CreateProductCommand) == {
        "merchant_id",
        "sku",
        "title",
        "description",
        "category",
        "price",
        "available_quantity",
        "idempotency_key",
    }
    assert field_names(AddProductImageCommand) == {
        "merchant_id",
        "product_id",
        "filename",
        "content_type",
        "content",
        "alt_text",
        "sort_order",
        "idempotency_key",
    }
    assert field_names(PurchaseProposalView) == {
        "id",
        "buyer_id",
        "merchant_id",
        "product_id",
        "product_version",
        "quantity",
        "unit_price",
        "total",
        "proposal_hash",
        "status",
        "next_required_gate",
        "expires_at",
        "created_at",
    }
    assert field_names(ApproveAuthorizationCommand) == {
        "proposal_id",
        "proposal_hash",
        "max_quantity",
        "max_amount",
        "expires_at",
        "idempotency_key",
    }
    assert field_names(TransactionView) == {
        "id",
        "proposal_id",
        "merchant_id",
        "buyer_id",
        "amount",
        "state",
        "provider_phase",
        "created_at",
        "updated_at",
    }
    assert field_names(ErrorEnvelope) == {"error", "correlation_id"}


def test_cross_lane_enum_values_are_frozen() -> None:
    assert enum_values(ActorType) == {"PLATFORM", "MERCHANT_USER", "BUYER", "SYSTEM"}
    assert enum_values(MerchantRole) == {"ADMIN", "EDITOR", "APPROVER", "VIEWER"}
    assert enum_values(ProductStatus) == {"DRAFT", "PUBLISHED", "UNPUBLISHED"}
    assert enum_values(PolicyMode) == {"MANUAL_ALL", "AUTO_BELOW_LIMIT", "DENY_ALL"}
    assert enum_values(AuthorizationStatus) == {"REQUESTED", "APPROVED", "REVOKED", "EXPIRED"}
    assert enum_values(MerchantDecisionValue) == {"ALLOW", "DENY", "REVIEW_REQUIRED"}
    assert enum_values(NextRequiredGate) == {
        "BUYER_AUTH_REQUIRED",
        "MERCHANT_POLICY_PENDING",
        "MERCHANT_REVIEW_REQUIRED",
        "READY",
    }
    assert enum_values(TransactionState) == {
        "PROPOSED",
        "BUYER_AUTH_REQUIRED",
        "MERCHANT_POLICY_PENDING",
        "MERCHANT_REVIEW_REQUIRED",
        "READY",
        "EXECUTING",
        "PAYMENT_PENDING",
        "UNKNOWN",
        "VERIFYING",
        "RECONCILING",
        "SUCCEEDED",
        "FAILED",
        "CANCELLED",
        "EXPIRED",
    }


def test_error_codes_and_id_prefixes_are_frozen() -> None:
    assert enum_values(ErrorCode) == {
        "UNAUTHENTICATED",
        "FORBIDDEN",
        "NOT_FOUND",
        "VALIDATION_ERROR",
        "PRODUCT_UNAVAILABLE",
        "PROPOSAL_STALE",
        "AUTHORIZATION_REQUIRED",
        "AUTHORIZATION_INVALID",
        "MERCHANT_REVIEW_REQUIRED",
        "POLICY_DENIED",
        "INVALID_STATE",
        "IDEMPOTENCY_KEY_REUSED",
        "PROVIDER_OUTCOME_UNKNOWN",
        "PROVIDER_ERROR",
        "INTERNAL_ERROR",
    }
    assert set(EntityPrefix.__args__) == {
        "mer",
        "musr",
        "prod",
        "pimg",
        "pol",
        "buy",
        "prop",
        "auth",
        "mdec",
        "txn",
        "idem",
        "pay",
        "pwh",
        "tevt",
    }


def test_provider_port_is_not_exported_from_public_contract_package() -> None:
    import ai_commerce_gateway.contracts as public_contracts

    assert not hasattr(public_contracts, "ProviderService")
