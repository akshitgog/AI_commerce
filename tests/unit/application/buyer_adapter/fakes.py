from datetime import UTC, datetime
from typing import Any

from ai_commerce_gateway.contracts.models import (
    ActorContext,
    ActorType,
    AuditPage,
    AuthorizationStatus,
    BuyerAuthorizationView,
    CatalogSearchQuery,
    CatalogSearchResult,
    CreateProposalCommand,
    CreateTransactionCommand,
    ExecuteTransactionCommand,
    Money,
    NextRequiredGate,
    ProductStatus,
    ProductView,
    ProposalStatus,
    PurchaseProposalView,
    RequestAuthorizationCommand,
    TransactionEventView,
    TransactionState,
    TransactionView,
)


class FakeCatalogService:
    def search(self, query: CatalogSearchQuery, actor: ActorContext) -> CatalogSearchResult:
        return CatalogSearchResult(
            items=(
                ProductView(
                    id="prod_fake_001",
                    merchant_id=query.merchant_id,
                    sku="FAKE-SKU-001",
                    title="Fake Widget",
                    description="A fake product for testing the buyer journey.",
                    category="Electronics",
                    price=Money(amount_minor=1000, currency="INR"),
                    available_quantity=10,
                    status=ProductStatus.PUBLISHED,
                    version=1,
                    images=(),
                ),
            )
        )

    def get_product(
        self, merchant_id: str, product_id: str, actor: ActorContext
    ) -> ProductView:
        return ProductView(
            id=product_id,
            merchant_id=merchant_id,
            sku="sku_1",
            title="Fake Product",
            description="A fake product for testing",
            price=Money(amount_minor=1000, currency="INR"),
            available_quantity=10,
            status=ProductStatus.PUBLISHED,
            version=1,
            images=(),
        )


class FakeProposalService:
    def create(self, command: CreateProposalCommand, actor: ActorContext) -> PurchaseProposalView:
        return PurchaseProposalView(
            id="prop_123",
            buyer_id=actor.actor_id,
            merchant_id=command.merchant_id,
            product_id=command.product_id,
            product_version=1,
            quantity=command.quantity,
            unit_price=Money(amount_minor=1000, currency="INR"),
            total=Money(amount_minor=1000 * command.quantity, currency="INR"),
            proposal_hash="hash",
            status=ProposalStatus.PROPOSED,
            next_required_gate=NextRequiredGate.BUYER_AUTH_REQUIRED,
            expires_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )

    def get(self, proposal_id: str, actor: ActorContext) -> PurchaseProposalView:
        raise NotImplementedError()


class FakeAuthorizationService:
    def __init__(self) -> None:
        self.approve_calls: list[Any] = []

    def request(
        self, command: RequestAuthorizationCommand, actor: ActorContext
    ) -> BuyerAuthorizationView:
        return BuyerAuthorizationView(
            id="auth_123",
            buyer_id=actor.actor_id,
            proposal_id=command.proposal_id,
            proposal_hash="hash",
            merchant_id="mer_123",
            product_id="prod_123",
            max_quantity=1,
            max_amount=Money(amount_minor=1000, currency="INR"),
            authorized_by=None,
            status=AuthorizationStatus.REQUESTED,
            expires_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )

    def approve(self, command: Any, actor: ActorContext) -> BuyerAuthorizationView:
        """Record the approval and return an APPROVED view bound to the actor."""
        self.approve_calls.append(command)
        return BuyerAuthorizationView(
            id="auth_123",
            buyer_id=actor.actor_id,
            proposal_id=command.proposal_id,
            proposal_hash=command.proposal_hash,
            merchant_id="mer_123",
            product_id="prod_123",
            max_quantity=command.max_quantity,
            max_amount=command.max_amount,
            authorized_by=actor.actor_id,
            status=AuthorizationStatus.APPROVED,
            expires_at=command.expires_at,
            created_at=datetime.now(UTC),
        )


class FakeTransactionService:
    def create(self, command: CreateTransactionCommand, actor: ActorContext) -> TransactionView:
        return TransactionView(
            id="txn_123",
            proposal_id=command.proposal_id,
            merchant_id="mer_123",
            buyer_id=actor.actor_id,
            amount=Money(amount_minor=1000, currency="INR"),
            state=TransactionState.READY,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def execute(self, command: ExecuteTransactionCommand, actor: ActorContext) -> TransactionView:
        return TransactionView(
            id=command.transaction_id,
            proposal_id="prop_123",
            merchant_id="mer_123",
            buyer_id=actor.actor_id,
            amount=Money(amount_minor=1000, currency="INR"),
            state=TransactionState.EXECUTING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def get_status(self, transaction_id: str, actor: ActorContext) -> TransactionView:
        return TransactionView(
            id=transaction_id,
            proposal_id="prop_123",
            merchant_id="mer_123",
            buyer_id=actor.actor_id,
            amount=Money(amount_minor=1000, currency="INR"),
            state=TransactionState.EXECUTING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def list_for_merchant(
        self, merchant_id: str, actor: ActorContext, cursor: str | None = None
    ) -> Any:
        raise NotImplementedError()

    def reconcile(self, command: Any, actor: ActorContext) -> TransactionView:
        raise NotImplementedError()

    def get_audit(
        self, transaction_id: str, actor: ActorContext, cursor: str | None = None
    ) -> AuditPage:
        event = TransactionEventView(
            id="evt_123",
            transaction_id=transaction_id,
            event_type="STATE_CHANGED",
            actor_type=ActorType.BUYER,
            actor_id=actor.actor_id,
            reason_code="EXECUTE_INVOKED",
            previous_state=TransactionState.READY,
            new_state=TransactionState.EXECUTING,
            correlation_id="corr_1",
            provider_reference_redacted="rzp_order_***123",
            metadata={},
            created_at=datetime.now(UTC),
        )
        return AuditPage(items=(event,), next_cursor=None)
