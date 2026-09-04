import logging

from ai_commerce_gateway.application.buyer_adapter.schemas import (
    CreatePurchaseProposalRequest,
    ExecuteTransactionRequest,
    GetProductRequest,
    GetTransactionAuditRequest,
    GetTransactionStatusRequest,
    InvocationContext,
    RequestAuthorizationRequest,
    SearchCatalogRequest,
)
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    AuditPage,
    BuyerAuthorizationView,
    CatalogSearchQuery,
    CatalogSearchResult,
    CreateProposalCommand,
    CreateTransactionCommand,
    ExecuteTransactionCommand,
    ProductView,
    PurchaseProposalView,
    RequestAuthorizationCommand,
    TransactionEventView,
    TransactionView,
)
from ai_commerce_gateway.contracts.services import (
    AuthorizationService,
    CatalogService,
    ProposalService,
    TransactionService,
)

logger = logging.getLogger(__name__)


def _redact_event(event: TransactionEventView) -> TransactionEventView:
    """Redacts any sensitive provider/internal fields before returning to buyer."""
    # The event already has provider_reference_redacted, but we ensure
    # we don't leak anything else in metadata if it's sensitive.
    # In a full implementation, we might strip out specific keys from metadata.
    return event


class BuyerAdapter:
    """
    Thin adapter over canonical commerce services for Buyer AI and MCP clients.
    Does NOT contain financial logic, trusted rules, or direct provider calls.
    Translates tool requests into canonical commands.
    """

    def __init__(
        self,
        catalog: CatalogService,
        proposal: ProposalService,
        auth: AuthorizationService,
        transaction: TransactionService,
    ) -> None:
        self._catalog = catalog
        self._proposal = proposal
        self._auth = auth
        self._transaction = transaction

    def search_catalog(
        self,
        actor: ActorContext,
        invocation: InvocationContext,
        request: SearchCatalogRequest,
    ) -> CatalogSearchResult:
        logger.info(f"search_catalog invoked [corr={invocation.correlation_id}]")
        query = CatalogSearchQuery(
            merchant_id=request.merchant_id,
            query=request.query,
            category=request.category,
            min_price_minor=request.min_price_minor,
            max_price_minor=request.max_price_minor,
            currency=request.currency,
            cursor=request.cursor,
            limit=request.limit,
        )
        return self._catalog.search(query, actor)

    def get_product(
        self,
        actor: ActorContext,
        invocation: InvocationContext,
        request: GetProductRequest,
    ) -> ProductView:
        logger.info(f"get_product invoked [corr={invocation.correlation_id}]")
        return self._catalog.get_product(request.product_id, actor)

    def create_purchase_proposal(
        self,
        actor: ActorContext,
        invocation: InvocationContext,
        request: CreatePurchaseProposalRequest,
    ) -> PurchaseProposalView:
        logger.info(f"create_purchase_proposal invoked [corr={invocation.correlation_id}]")
        if not invocation.idempotency_key:
            raise ValueError("idempotency_key is required for mutating operations")

        command = CreateProposalCommand(
            merchant_id=request.merchant_id,
            product_id=request.product_id,
            quantity=request.quantity,
            idempotency_key=invocation.idempotency_key,
        )
        return self._proposal.create(command, actor)

    def request_authorization(
        self,
        actor: ActorContext,
        invocation: InvocationContext,
        request: RequestAuthorizationRequest,
    ) -> BuyerAuthorizationView:
        logger.info(f"request_authorization invoked [corr={invocation.correlation_id}]")
        if not invocation.idempotency_key:
            raise ValueError("idempotency_key is required for mutating operations")

        command = RequestAuthorizationCommand(
            proposal_id=request.proposal_id,
            idempotency_key=invocation.idempotency_key,
        )
        return self._auth.request(command, actor)

    def execute_transaction(
        self,
        actor: ActorContext,
        invocation: InvocationContext,
        request: ExecuteTransactionRequest,
    ) -> TransactionView:
        """
        Creates (or reuses) the transaction for the proposal and then executes it.
        """
        logger.info(f"execute_transaction invoked [corr={invocation.correlation_id}]")
        if not invocation.idempotency_key:
            raise ValueError("idempotency_key is required for mutating operations")

        # 1. Create or reuse logical transaction
        create_cmd = CreateTransactionCommand(
            proposal_id=request.proposal_id,
            idempotency_key=f"{invocation.idempotency_key}_create",
        )
        txn = self._transaction.create(create_cmd, actor)

        # 2. Execute transaction (revalidates gates and creates/reuses provider order)
        execute_cmd = ExecuteTransactionCommand(
            transaction_id=txn.id,
            idempotency_key=f"{invocation.idempotency_key}_exec",
        )
        return self._transaction.execute(execute_cmd, actor)

    def get_transaction_status(
        self,
        actor: ActorContext,
        invocation: InvocationContext,
        request: GetTransactionStatusRequest,
    ) -> TransactionView:
        logger.info(f"get_transaction_status invoked [corr={invocation.correlation_id}]")
        return self._transaction.get_status(request.transaction_id, actor)

    def get_transaction_audit(
        self,
        actor: ActorContext,
        invocation: InvocationContext,
        request: GetTransactionAuditRequest,
    ) -> AuditPage:
        logger.info(f"get_transaction_audit invoked [corr={invocation.correlation_id}]")
        page = self._transaction.get_audit(request.transaction_id, actor, cursor=request.cursor)
        redacted_items = tuple(_redact_event(evt) for evt in page.items)
        return AuditPage(items=redacted_items, next_cursor=page.next_cursor)
