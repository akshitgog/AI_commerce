from typing import get_protocol_members

from ai_commerce_gateway.contracts.services import (
    AuthorizationService,
    CatalogService,
    MerchantPolicyService,
    ProviderService,
    StorageService,
    TransactionService,
)


def test_shared_service_method_names_are_frozen() -> None:
    assert get_protocol_members(CatalogService) == {"get_product", "search"}
    assert get_protocol_members(AuthorizationService) == {"approve", "request"}
    assert get_protocol_members(MerchantPolicyService) == {
        "evaluate",
        "record_manual_decision",
    }
    assert get_protocol_members(TransactionService) == {
        "create",
        "execute",
        "get_audit",
        "get_status",
        "reconcile",
    }
    assert get_protocol_members(ProviderService) == {
        "create_order",
        "handle_webhook",
        "lookup_order",
        "lookup_payment",
        "verify_checkout",
    }
    assert get_protocol_members(StorageService) == {
        "delete_product_image",
        "get_public_url",
        "upload_product_image",
    }
