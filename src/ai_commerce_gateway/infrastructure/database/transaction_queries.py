from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.application.transaction_service import TransactionQueryRepository
from ai_commerce_gateway.contracts.models import TransactionEventView
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ActorType, TransactionState
from ai_commerce_gateway.domain.transactions import Transaction
from ai_commerce_gateway.infrastructure.database import models
from ai_commerce_gateway.infrastructure.database.execution import SqlAlchemyExecutionRepository

_PAGE_SIZE = 50


class SqlAlchemyTransactionQueryRepository(SqlAlchemyExecutionRepository):
    """Stable, cursor-paginated read model over canonical transaction records."""

    def list_transactions_for_buyer(
        self, buyer_id: str, cursor: str | None
    ) -> tuple[tuple[Transaction, ...], str | None]:
        statement = select(models.Transaction).join(models.Proposal, models.Transaction.proposal_id == models.Proposal.id).where(
            models.Proposal.buyer_id == buyer_id
        )
        if cursor is not None:
            anchor = self._session.get(models.Transaction, cursor)
            if anchor is None:
                raise _invalid_cursor()
            statement = statement.where(
                or_(
                    models.Transaction.created_at < anchor.created_at,
                    and_(
                        models.Transaction.created_at == anchor.created_at,
                        models.Transaction.id < anchor.id,
                    ),
                )
            )
        records = list(
            self._session.scalars(
                statement.order_by(
                    models.Transaction.created_at.desc(), models.Transaction.id.desc()
                ).limit(_PAGE_SIZE + 1)
            )
        )
        has_more = len(records) > _PAGE_SIZE
        page = records[:_PAGE_SIZE]
        next_cursor = page[-1].id if has_more else None
        return tuple(_transaction_to_domain(record) for record in page), next_cursor

    def list_transactions(
        self, merchant_id: str, cursor: str | None
    ) -> tuple[tuple[Transaction, ...], str | None]:
        statement = select(models.Transaction).where(
            models.Transaction.merchant_id == merchant_id
        )
        if cursor is not None:
            anchor = self._session.get(models.Transaction, cursor)
            if anchor is None or anchor.merchant_id != merchant_id:
                raise _invalid_cursor()
            statement = statement.where(
                or_(
                    models.Transaction.created_at < anchor.created_at,
                    and_(
                        models.Transaction.created_at == anchor.created_at,
                        models.Transaction.id < anchor.id,
                    ),
                )
            )
        records = list(
            self._session.scalars(
                statement.order_by(
                    models.Transaction.created_at.desc(), models.Transaction.id.desc()
                ).limit(_PAGE_SIZE + 1)
            )
        )
        has_more = len(records) > _PAGE_SIZE
        page = records[:_PAGE_SIZE]
        next_cursor = page[-1].id if has_more and page else None
        return tuple(self._transaction_to_domain(record) for record in page), next_cursor

    def list_events(
        self, transaction_id: str, cursor: str | None
    ) -> tuple[tuple[TransactionEventView, ...], str | None]:
        statement = select(models.TransactionEvent).where(
            models.TransactionEvent.transaction_id == transaction_id
        )
        if cursor is not None:
            anchor = self._session.get(models.TransactionEvent, cursor)
            if anchor is None or anchor.transaction_id != transaction_id:
                raise _invalid_cursor()
            statement = statement.where(
                or_(
                    models.TransactionEvent.created_at > anchor.created_at,
                    and_(
                        models.TransactionEvent.created_at == anchor.created_at,
                        models.TransactionEvent.id > anchor.id,
                    ),
                )
            )
        records = list(
            self._session.scalars(
                statement.order_by(
                    models.TransactionEvent.created_at.asc(),
                    models.TransactionEvent.id.asc(),
                ).limit(_PAGE_SIZE + 1)
            )
        )
        has_more = len(records) > _PAGE_SIZE
        page = records[:_PAGE_SIZE]
        next_cursor = page[-1].id if has_more and page else None
        return tuple(_event_view(record) for record in page), next_cursor


class SqlAlchemyTransactionQueryUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self.repository: TransactionQueryRepository

    def __enter__(self) -> "SqlAlchemyTransactionQueryUnitOfWork":
        self._session = self._session_factory()
        self.repository = SqlAlchemyTransactionQueryRepository(self._session)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._session is not None:
            self._session.rollback()
            self._session.close()
            self._session = None


def _event_view(record: models.TransactionEvent) -> TransactionEventView:
    return TransactionEventView(
        id=record.id,
        transaction_id=record.transaction_id,
        event_type=record.event_type,
        actor_type=ActorType(record.actor_type),
        actor_id=record.actor_id,
        reason_code=record.reason_code,
        previous_state=(
            TransactionState(record.previous_state)
            if record.previous_state is not None
            else None
        ),
        new_state=(TransactionState(record.new_state) if record.new_state is not None else None),
        correlation_id=record.correlation_id,
        provider_reference_redacted=record.provider_reference_redacted,
        metadata=dict(record.metadata_json),
        created_at=_as_utc(record.created_at),
    )


def _invalid_cursor() -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, "Pagination cursor is invalid.", status_code=400)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
