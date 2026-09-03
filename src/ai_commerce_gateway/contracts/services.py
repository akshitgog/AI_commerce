from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from typing import BinaryIO, Protocol

from ai_commerce_gateway.contracts.models import (
    ActorContext,
    ApproveAuthorizationCommand,
    AuditPage,
    BuyerAuthorizationView,
    CatalogSearchQuery,
    CatalogSearchResult,
    CreateProposalCommand,
    CreateProviderOrderCommand,
    CreateTransactionCommand,
    EvaluateMerchantPolicyCommand,
    ExecuteTransactionCommand,
    HandleWebhookCommand,
    MerchantDecisionView,
    ProductView,
    ProviderEvidence,
    ProviderLookupCommand,
    ReconcileTransactionCommand,
    RecordMerchantDecisionCommand,
    RequestAuthorizationCommand,
    StoredImage,
    TransactionView,
    VerifyCheckoutCommand,
)


class CatalogService(Protocol):
    async def search(
        self, query: CatalogSearchQuery, actor: ActorContext
    ) -> CatalogSearchResult: ...
    async def get_product(self, product_id: str, actor: ActorContext) -> ProductView: ...


class ProposalService(Protocol):
    async def create(
        self, command: CreateProposalCommand, actor: ActorContext
    ) -> "PurchaseProposalView": ...


class AuthorizationService(Protocol):
    async def request(
        self, command: RequestAuthorizationCommand, actor: ActorContext
    ) -> BuyerAuthorizationView: ...
    async def approve(
        self, command: ApproveAuthorizationCommand, actor: ActorContext
    ) -> BuyerAuthorizationView: ...


class MerchantPolicyService(Protocol):
    async def evaluate(
        self, command: EvaluateMerchantPolicyCommand, actor: ActorContext
    ) -> MerchantDecisionView: ...
    async def record_manual_decision(
        self, command: RecordMerchantDecisionCommand, actor: ActorContext
    ) -> MerchantDecisionView: ...


class TransactionService(Protocol):
    async def create(
        self, command: CreateTransactionCommand, actor: ActorContext
    ) -> TransactionView: ...
    async def execute(
        self, command: ExecuteTransactionCommand, actor: ActorContext
    ) -> TransactionView: ...
    async def get_status(self, transaction_id: str, actor: ActorContext) -> TransactionView: ...
    async def reconcile(
        self, command: ReconcileTransactionCommand, actor: ActorContext
    ) -> TransactionView: ...
    async def get_audit(
        self, transaction_id: str, actor: ActorContext, cursor: str | None = None
    ) -> AuditPage: ...


class ProviderService(Protocol):
    async def create_order(self, command: CreateProviderOrderCommand) -> ProviderEvidence: ...
    async def verify_checkout(self, command: VerifyCheckoutCommand) -> ProviderEvidence: ...
    async def handle_webhook(self, command: HandleWebhookCommand) -> ProviderEvidence: ...
    async def lookup_order(self, command: ProviderLookupCommand) -> ProviderEvidence: ...
    async def lookup_payment(self, command: ProviderLookupCommand) -> ProviderEvidence: ...


class StorageService(Protocol):
    async def upload_product_image(
        self, *, merchant_id: str, product_id: str, filename: str, content: BinaryIO
    ) -> StoredImage: ...
    async def delete_product_image(self, *, storage_path: str) -> None: ...
    async def get_public_url(self, *, storage_path: str) -> str: ...


class UnitOfWork(Protocol):
    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


UnitOfWorkFactory = AbstractAsyncContextManager[UnitOfWork]
EventStream = AsyncIterator[object]


# Imported last to keep the protocol section readable and avoid circular annotations.
from ai_commerce_gateway.contracts.models import PurchaseProposalView  # noqa: E402
