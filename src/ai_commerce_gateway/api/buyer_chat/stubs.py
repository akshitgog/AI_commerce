"""Fake/stub application services for the buyer chat demo and tests.

These are wired into the FastAPI app via dependency injection.
Real implementations (from workstreams 02/03) will replace these when available.
"""

from datetime import UTC, datetime

from ai_commerce_gateway.contracts.models import (
    ActorContext,
    AuditPage,
    BuyerAuthorizationView,
    CatalogSearchQuery,
    CatalogSearchResult,
    CreateProposalCommand,
    CreateTransactionCommand,
    ExecuteTransactionCommand,
    Money,
    ProductView,
    PurchaseProposalView,
    ReconcileTransactionCommand,
    RequestAuthorizationCommand,
    TransactionPage,
    TransactionView,
)
from ai_commerce_gateway.contracts.services import (
    AuthorizationService,
    CatalogService,
    ProposalService,
    TransactionService,
)
from ai_commerce_gateway.domain.enums import (
    AuthorizationStatus,
    NextRequiredGate,
    ProductStatus,
    ProposalStatus,
    TransactionState,
)


class StubCatalogService:
    """Stub catalog service for C2 demo. Replaced by real implementation at integration."""

    def search(self, query: CatalogSearchQuery, actor: ActorContext) -> CatalogSearchResult:
        stub_product = ProductView(
            id="prod_demo_001",
            merchant_id=query.merchant_id,
            sku="DEMO-SKU-001",
            title="Demo Widget",
            description="A demo product for the buyer chat journey.",
            category="Electronics",
            price=Money(amount_minor=49900, currency="INR"),
            available_quantity=50,
            status=ProductStatus.PUBLISHED,
            version=1,
            images=(),
        )
        return CatalogSearchResult(items=(stub_product,))

    def get_product(self, product_id: str, actor: ActorContext) -> ProductView:
        return ProductView(
            id=product_id,
            merchant_id="mer_demo_001",
            sku="DEMO-SKU-001",
            title="Demo Widget",
            description="A demo product for the buyer chat journey.",
            category="Electronics",
            price=Money(amount_minor=49900, currency="INR"),
            available_quantity=50,
            status=ProductStatus.PUBLISHED,
            version=1,
            images=(),
        )


class StubProposalService:
    """Stub proposal service. Total is derived server-side, never from client input."""

    def create(self, command: CreateProposalCommand, actor: ActorContext) -> PurchaseProposalView:
        unit_price = Money(amount_minor=49900, currency="INR")
        total = Money(amount_minor=49900 * command.quantity, currency="INR")
        return PurchaseProposalView(
            id="prop_demo_001",
            buyer_id=actor.actor_id,
            merchant_id=command.merchant_id,
            product_id=command.product_id,
            product_version=1,
            quantity=command.quantity,
            unit_price=unit_price,
            total=total,
            proposal_hash="demo_hash_abc123",
            status=ProposalStatus.PROPOSED,
            next_required_gate=NextRequiredGate.BUYER_AUTH_REQUIRED,
            expires_at=datetime(2026, 12, 31, tzinfo=UTC),
            created_at=datetime.now(UTC),
        )

    def get(self, proposal_id: str, actor: ActorContext) -> PurchaseProposalView:
        raise NotImplementedError("Stub: get proposal not implemented in C2")


class StubAuthorizationService:
    """Stub authorization service. Cannot approve — only requests."""

    def request(
        self, command: RequestAuthorizationCommand, actor: ActorContext
    ) -> BuyerAuthorizationView:
        return BuyerAuthorizationView(
            id="auth_demo_001",
            buyer_id=actor.actor_id,
            proposal_id=command.proposal_id,
            proposal_hash="demo_hash_abc123",
            merchant_id="mer_demo_001",
            product_id="prod_demo_001",
            max_quantity=1,
            max_amount=Money(amount_minor=49900, currency="INR"),
            authorized_by=None,
            status=AuthorizationStatus.REQUESTED,
            expires_at=datetime(2026, 12, 31, tzinfo=UTC),
            created_at=datetime.now(UTC),
        )

    def approve(self, command: object, actor: ActorContext) -> BuyerAuthorizationView:
        raise NotImplementedError("Adapter cannot approve authorization")


class StubTransactionService:
    """Stub transaction service. Delegates to authority, never executes provider logic."""

    def create(self, command: CreateTransactionCommand, actor: ActorContext) -> TransactionView:
        return TransactionView(
            id="txn_demo_001",
            proposal_id=command.proposal_id,
            merchant_id="mer_demo_001",
            buyer_id=actor.actor_id,
            amount=Money(amount_minor=49900, currency="INR"),
            state=TransactionState.READY,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def execute(self, command: ExecuteTransactionCommand, actor: ActorContext) -> TransactionView:
        return TransactionView(
            id=command.transaction_id,
            proposal_id="prop_demo_001",
            merchant_id="mer_demo_001",
            buyer_id=actor.actor_id,
            amount=Money(amount_minor=49900, currency="INR"),
            state=TransactionState.EXECUTING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def get_status(self, transaction_id: str, actor: ActorContext) -> TransactionView:
        return TransactionView(
            id=transaction_id,
            proposal_id="prop_demo_001",
            merchant_id="mer_demo_001",
            buyer_id=actor.actor_id,
            amount=Money(amount_minor=49900, currency="INR"),
            state=TransactionState.EXECUTING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def list_for_merchant(
        self, merchant_id: str, actor: ActorContext, cursor: str | None = None
    ) -> TransactionPage:
        raise NotImplementedError

    def reconcile(
        self, command: ReconcileTransactionCommand, actor: ActorContext
    ) -> TransactionView:
        raise NotImplementedError

    def get_audit(
        self, transaction_id: str, actor: ActorContext, cursor: str | None = None
    ) -> AuditPage:
        return AuditPage(items=(), next_cursor=None)


# Singleton stubs for dependency injection.
# Replaced at integration with real service implementations.
_catalog_stub: CatalogService = StubCatalogService()
_proposal_stub: ProposalService = StubProposalService()
_auth_stub: AuthorizationService = StubAuthorizationService()
_transaction_stub: TransactionService = StubTransactionService()


def get_catalog_service() -> CatalogService:
    return _catalog_stub


def get_proposal_service() -> ProposalService:
    return _proposal_stub


def get_auth_service() -> AuthorizationService:
    return _auth_stub


def get_transaction_service() -> TransactionService:
    return _transaction_stub
