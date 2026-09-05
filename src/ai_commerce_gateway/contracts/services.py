from collections.abc import Callable
from typing import Protocol

from ai_commerce_gateway.contracts.models import (
    ActorContext,
    AddProductImageCommand,
    ApproveAuthorizationCommand,
    AuditPage,
    BuyerAuthorizationView,
    CatalogSearchQuery,
    CatalogSearchResult,
    CreateMerchantCommand,
    CreateProductCommand,
    CreateProposalCommand,
    CreateTransactionCommand,
    DeleteProductImageCommand,
    EvaluateMerchantPolicyCommand,
    ExecuteTransactionCommand,
    MerchantDecisionView,
    MerchantPolicyView,
    MerchantReviewPage,
    MerchantView,
    ProductImageView,
    ProductPage,
    ProductView,
    PurchaseProposalView,
    ReconcileTransactionCommand,
    RecordMerchantDecisionCommand,
    RequestAuthorizationCommand,
    SetProductPublicationCommand,
    StoredImage,
    TransactionPage,
    TransactionView,
    UpdateMerchantPolicyCommand,
    UpdateProductCommand,
)


class CatalogService(Protocol):
    def search(self, query: CatalogSearchQuery, actor: ActorContext) -> CatalogSearchResult: ...
    def get_product(
        self, merchant_id: str, product_id: str, actor: ActorContext
    ) -> ProductView: ...  # noqa: E501


class MerchantCatalogService(Protocol):
    def create_merchant(
        self, command: CreateMerchantCommand, actor: ActorContext
    ) -> MerchantView: ...
    def get_merchant(self, merchant_id: str, actor: ActorContext) -> MerchantView: ...
    def get_product(self, product_id: str, actor: ActorContext) -> ProductView: ...
    def list_products(
        self, merchant_id: str, actor: ActorContext, cursor: str | None = None
    ) -> ProductPage: ...
    def create_product(self, command: CreateProductCommand, actor: ActorContext) -> ProductView: ...  # noqa: E501
    def update_product(self, command: UpdateProductCommand, actor: ActorContext) -> ProductView: ...  # noqa: E501
    def publish_product(
        self, command: SetProductPublicationCommand, actor: ActorContext
    ) -> ProductView: ...
    def unpublish_product(
        self, command: SetProductPublicationCommand, actor: ActorContext
    ) -> ProductView: ...
    def add_product_image(
        self, command: AddProductImageCommand, actor: ActorContext
    ) -> ProductImageView: ...
    def delete_product_image(
        self, command: DeleteProductImageCommand, actor: ActorContext
    ) -> None: ...


class ProposalService(Protocol):
    def create(
        self, command: CreateProposalCommand, actor: ActorContext
    ) -> PurchaseProposalView: ...
    def get(self, proposal_id: str, actor: ActorContext) -> PurchaseProposalView: ...


class AuthorizationService(Protocol):
    def request(
        self, command: RequestAuthorizationCommand, actor: ActorContext
    ) -> BuyerAuthorizationView: ...
    def approve(
        self, command: ApproveAuthorizationCommand, actor: ActorContext
    ) -> BuyerAuthorizationView: ...


class MerchantPolicyService(Protocol):
    def get_policy(self, merchant_id: str, actor: ActorContext) -> MerchantPolicyView: ...
    def update_policy(
        self, command: UpdateMerchantPolicyCommand, actor: ActorContext
    ) -> MerchantPolicyView: ...
    def list_reviews(
        self, merchant_id: str, actor: ActorContext, cursor: str | None = None
    ) -> MerchantReviewPage: ...
    def evaluate(
        self, command: EvaluateMerchantPolicyCommand, actor: ActorContext
    ) -> MerchantDecisionView: ...
    def record_manual_decision(
        self, command: RecordMerchantDecisionCommand, actor: ActorContext
    ) -> MerchantDecisionView: ...


class TransactionService(Protocol):
    def create(self, command: CreateTransactionCommand, actor: ActorContext) -> TransactionView: ...
    def execute(
        self, command: ExecuteTransactionCommand, actor: ActorContext
    ) -> TransactionView: ...
    def get_status(self, transaction_id: str, actor: ActorContext) -> TransactionView: ...
    def list_for_merchant(
        self, merchant_id: str, actor: ActorContext, cursor: str | None = None
    ) -> TransactionPage: ...
    def reconcile(
        self, command: ReconcileTransactionCommand, actor: ActorContext
    ) -> TransactionView: ...
    def get_audit(
        self, transaction_id: str, actor: ActorContext, cursor: str | None = None
    ) -> AuditPage: ...


class StorageService(Protocol):
    def upload_product_image(
        self,
        *,
        merchant_id: str,
        product_id: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> StoredImage: ...
    def delete_product_image(self, *, storage_path: str) -> None: ...
    def get_public_url(self, *, storage_path: str) -> str: ...


class UnitOfWork(Protocol):
    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
