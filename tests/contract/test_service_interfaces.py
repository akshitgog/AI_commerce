from inspect import iscoroutinefunction, signature
from typing import get_protocol_members

from ai_commerce_gateway.contracts.provider import ProviderService
from ai_commerce_gateway.contracts.services import (
    AuthorizationService,
    CatalogService,
    MerchantCatalogService,
    MerchantPolicyService,
    ProposalService,
    StorageService,
    TransactionService,
    UnitOfWork,
)


def test_shared_service_method_names_are_frozen() -> None:
    assert get_protocol_members(CatalogService) == {"get_product", "search"}
    assert get_protocol_members(MerchantCatalogService) == {
        "add_product_image",
        "create_merchant",
        "create_product",
        "delete_product_image",
        "get_merchant",
        "get_product",
        "list_products",
        "publish_product",
        "unpublish_product",
        "update_product",
    }
    assert get_protocol_members(ProposalService) == {"create", "get"}
    assert get_protocol_members(AuthorizationService) == {"approve", "request"}
    assert get_protocol_members(MerchantPolicyService) == {
        "evaluate",
        "get_policy",
        "list_reviews",
        "record_manual_decision",
        "update_policy",
    }
    assert get_protocol_members(TransactionService) == {
        "create",
        "execute",
        "get_audit",
        "get_status",
        "list_for_merchant",
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
    assert get_protocol_members(UnitOfWork) == {
        "__enter__",
        "__exit__",
        "commit",
        "rollback",
    }


def test_boundary_method_parameters_and_sync_model_are_frozen() -> None:
    expected_parameters = {
        CatalogService.search: ["self", "query", "actor"],
        MerchantCatalogService.create_product: ["self", "command", "actor"],
        ProposalService.create: ["self", "command", "actor"],
        AuthorizationService.approve: ["self", "command", "actor"],
        MerchantPolicyService.record_manual_decision: ["self", "command", "actor"],
        TransactionService.execute: ["self", "command", "actor"],
        TransactionService.reconcile: ["self", "command", "actor"],
        ProviderService.create_order: ["self", "command"],
        ProviderService.verify_checkout: ["self", "command"],
        ProviderService.handle_webhook: ["self", "command"],
        StorageService.upload_product_image: [
            "self",
            "merchant_id",
            "product_id",
            "filename",
            "content_type",
            "content",
        ],
    }
    for method, parameters in expected_parameters.items():
        assert list(signature(method).parameters) == parameters
        assert not iscoroutinefunction(method)

    assert not iscoroutinefunction(UnitOfWork.commit)
    assert not iscoroutinefunction(UnitOfWork.rollback)
