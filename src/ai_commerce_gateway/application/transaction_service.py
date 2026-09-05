from collections.abc import Callable
from typing import Protocol

from ai_commerce_gateway.contracts.models import (
    ActorContext,
    AuditPage,
    CreateTransactionCommand,
    ExecuteTransactionCommand,
    Money,
    ProviderPhase,
    ReconcileTransactionCommand,
    TransactionEventView,
    TransactionPage,
    TransactionView,
)
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ActorType
from ai_commerce_gateway.domain.execution import PaymentAttempt
from ai_commerce_gateway.domain.transactions import Transaction


class TransactionQueryRepository(Protocol):
    def get_transaction(self, transaction_id: str) -> Transaction | None: ...
    def get_payment_attempt(self, transaction_id: str) -> PaymentAttempt | None: ...
    def list_transactions(
        self, merchant_id: str, cursor: str | None
    ) -> tuple[tuple[Transaction, ...], str | None]: ...
    def list_transactions_for_buyer(
        self, buyer_id: str, cursor: str | None
    ) -> tuple[tuple[Transaction, ...], str | None]: ...
    def list_events(
        self, transaction_id: str, cursor: str | None
    ) -> tuple[tuple[TransactionEventView, ...], str | None]: ...


class TransactionQueryUnitOfWork(Protocol):
    repository: TransactionQueryRepository

    def __enter__(self) -> "TransactionQueryUnitOfWork": ...
    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None: ...


QueryUnitOfWorkFactory = Callable[[], TransactionQueryUnitOfWork]


class TransactionQueryApplicationService:
    """Tenant-safe read side for transaction status, merchant lists, and audit."""

    def __init__(self, unit_of_work_factory: QueryUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def get_status(self, transaction_id: str, actor: ActorContext) -> TransactionView:
        with self._unit_of_work_factory() as unit_of_work:
            transaction = _get_transaction(unit_of_work.repository, transaction_id)
            _require_transaction_access(actor, transaction)
            attempt = unit_of_work.repository.get_payment_attempt(transaction.id)
            return _transaction_view(transaction, attempt)

    def list_for_merchant(
        self, merchant_id: str, actor: ActorContext, cursor: str | None = None
    ) -> TransactionPage:
        _require_merchant_list_access(actor, merchant_id)
        with self._unit_of_work_factory() as unit_of_work:
            transactions, next_cursor = unit_of_work.repository.list_transactions(
                merchant_id, cursor
            )
            items = tuple(
                _transaction_view(
                    transaction,
                    unit_of_work.repository.get_payment_attempt(transaction.id),
                )
                for transaction in transactions
            )
        return TransactionPage(items=items, next_cursor=next_cursor)

    def list_for_buyer(
        self, buyer_id: str, actor: ActorContext, cursor: str | None = None
    ) -> TransactionPage:
        if actor.actor_id != buyer_id:
            from ai_commerce_gateway.core.errors import AppError, ErrorCode
            raise AppError(ErrorCode.FORBIDDEN, "Not authorized.")
        with self._unit_of_work_factory() as unit_of_work:
            transactions, next_cursor = unit_of_work.repository.list_transactions_for_buyer(
                buyer_id, cursor
            )
            items = tuple(
                _transaction_view(
                    transaction,
                    unit_of_work.repository.get_payment_attempt(transaction.id),
                )
                for transaction in transactions
            )
        return TransactionPage(items=items, next_cursor=next_cursor)

    def get_audit(
        self, transaction_id: str, actor: ActorContext, cursor: str | None = None
    ) -> AuditPage:
        with self._unit_of_work_factory() as unit_of_work:
            transaction = _get_transaction(unit_of_work.repository, transaction_id)
            _require_transaction_access(actor, transaction)
            events, next_cursor = unit_of_work.repository.list_events(transaction.id, cursor)
        return AuditPage(items=events, next_cursor=next_cursor)


class TransactionCreatePort(Protocol):
    def create(
        self, command: CreateTransactionCommand, actor: ActorContext
    ) -> TransactionView: ...


class TransactionExecutePort(Protocol):
    def execute(
        self, command: ExecuteTransactionCommand, actor: ActorContext
    ) -> TransactionView: ...


class TransactionReconcilePort(Protocol):
    def reconcile(
        self, command: ReconcileTransactionCommand, actor: ActorContext
    ) -> TransactionView: ...


class TransactionApplicationService:
    """One implementation of the frozen TransactionService contract.

    The facade deliberately delegates mutations to the canonical gate, execution, and
    reconciliation services. It adds no alternate provider or state-transition path.
    """

    def __init__(
        self,
        *,
        creation: TransactionCreatePort,
        execution: TransactionExecutePort,
        reconciliation: TransactionReconcilePort,
        queries: TransactionQueryApplicationService,
        commit_created_transaction: Callable[[], None] | None = None,
    ) -> None:
        self._creation = creation
        self._execution = execution
        self._reconciliation = reconciliation
        self._queries = queries
        self._commit_created_transaction = commit_created_transaction

    def create(
        self, command: CreateTransactionCommand, actor: ActorContext
    ) -> TransactionView:
        transaction = self._creation.create(command, actor)
        if self._commit_created_transaction is not None:
            # Execution opens a fresh, locking unit of work. Persist the READY
            # transaction before that unit of work attempts to lock it.
            self._commit_created_transaction()
        return transaction

    def execute(
        self, command: ExecuteTransactionCommand, actor: ActorContext
    ) -> TransactionView:
        return self._execution.execute(command, actor)

    def get_status(self, transaction_id: str, actor: ActorContext) -> TransactionView:
        return self._queries.get_status(transaction_id, actor)

    def list_for_merchant(
        self, merchant_id: str, actor: ActorContext, cursor: str | None = None
    ) -> TransactionPage:
        return self._queries.list_for_merchant(merchant_id, actor, cursor)

    def list_for_buyer(
        self, buyer_id: str, actor: ActorContext, cursor: str | None = None
    ) -> TransactionPage:
        return self._queries.list_for_buyer(buyer_id, actor, cursor)

    def reconcile(
        self, command: ReconcileTransactionCommand, actor: ActorContext
    ) -> TransactionView:
        return self._reconciliation.reconcile(command, actor)

    def get_audit(
        self, transaction_id: str, actor: ActorContext, cursor: str | None = None
    ) -> AuditPage:
        return self._queries.get_audit(transaction_id, actor, cursor)


def _get_transaction(
    repository: TransactionQueryRepository, transaction_id: str
) -> Transaction:
    transaction = repository.get_transaction(transaction_id)
    if transaction is None:
        raise AppError(ErrorCode.NOT_FOUND, "Transaction was not found.", status_code=404)
    return transaction


def _require_transaction_access(actor: ActorContext, transaction: Transaction) -> None:
    buyer_access = actor.actor_type is ActorType.BUYER and actor.actor_id == transaction.buyer_id
    merchant_access = (
        actor.actor_type is ActorType.MERCHANT_USER
        and transaction.merchant_id in actor.merchant_ids
    )
    system_access = actor.actor_type in {ActorType.PLATFORM, ActorType.SYSTEM}
    if not (buyer_access or merchant_access or system_access):
        raise AppError(ErrorCode.FORBIDDEN, "Transaction access is forbidden.", status_code=403)


def _require_merchant_list_access(actor: ActorContext, merchant_id: str) -> None:
    merchant_access = (
        actor.actor_type is ActorType.MERCHANT_USER and merchant_id in actor.merchant_ids
    )
    system_access = actor.actor_type in {ActorType.PLATFORM, ActorType.SYSTEM}
    if not (merchant_access or system_access):
        raise AppError(
            ErrorCode.FORBIDDEN,
            "Merchant transaction access is forbidden.",
            status_code=403,
        )


def _transaction_view(transaction: Transaction, attempt: PaymentAttempt | None) -> TransactionView:
    provider_phase = None
    if attempt is not None:
        provider_phase = ProviderPhase(
            provider=attempt.provider,
            provider_order_id=attempt.provider_order_id,
            order_state=attempt.provider_order_state,
            payment_state=attempt.provider_payment_state,
            capture_state=attempt.capture_state,
            last_verified_at=attempt.last_verified_at,
        )
    return TransactionView(
        id=transaction.id,
        proposal_id=transaction.proposal_id,
        merchant_id=transaction.merchant_id,
        buyer_id=transaction.buyer_id,
        amount=Money(amount_minor=transaction.amount_minor, currency=transaction.currency),
        state=transaction.state,
        provider_phase=provider_phase,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
    )
