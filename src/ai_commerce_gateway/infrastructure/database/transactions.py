from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.core.ids import new_id
from ai_commerce_gateway.domain.enums import ActorType, TransactionState
from ai_commerce_gateway.domain.transactions import Transaction, TransactionTransition
from ai_commerce_gateway.infrastructure.database.models import (
    Transaction as TransactionRecord,
)
from ai_commerce_gateway.infrastructure.database.models import (
    TransactionEvent as TransactionEventRecord,
)

EventIdFactory = Callable[[], str]
Clock = Callable[[], datetime]


class SqlAlchemyTransactionStateRepository:
    """Persist one validated state change and its causal event in the caller's transaction."""

    def __init__(
        self,
        session: Session,
        *,
        event_id_factory: EventIdFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._session = session
        self._event_id_factory = event_id_factory or (lambda: new_id("tevt"))
        self._clock = clock or (lambda: datetime.now(UTC))

    def transition(
        self,
        transaction_id: str,
        new_state: TransactionState,
        *,
        actor_type: ActorType,
        actor_id: str | None,
        reason_code: str,
        correlation_id: str,
        provider_reference_redacted: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> TransactionTransition:
        record = self._session.get(TransactionRecord, transaction_id)
        if record is None:
            raise AppError(
                ErrorCode.NOT_FOUND,
                "Transaction was not found.",
                status_code=404,
                details={"transaction_id": transaction_id},
            )

        transition = self._to_domain(record).transition(
            new_state,
            actor_type=actor_type,
            actor_id=actor_id,
            reason_code=reason_code,
            correlation_id=correlation_id,
            provider_reference_redacted=provider_reference_redacted,
            metadata=metadata,
            event_id=self._event_id_factory(),
            occurred_at=self._clock(),
        )
        record.state = transition.transaction.state.value
        record.updated_at = transition.transaction.updated_at
        self._session.add(
            TransactionEventRecord(
                id=transition.event.id,
                transaction_id=transition.event.transaction_id,
                event_type=transition.event.event_type,
                actor_type=transition.event.actor_type.value,
                actor_id=transition.event.actor_id,
                reason_code=transition.event.reason_code,
                previous_state=transition.event.previous_state.value,
                new_state=transition.event.new_state.value,
                correlation_id=transition.event.correlation_id,
                provider_reference_redacted=transition.event.provider_reference_redacted,
                metadata_json=deep_mutable_copy(transition.event.metadata),
                created_at=transition.event.created_at,
            )
        )
        self._session.flush()
        return transition

    @staticmethod
    def _to_domain(record: TransactionRecord) -> Transaction:
        return Transaction(
            id=record.id,
            proposal_id=record.proposal_id,
            buyer_authorization_id=record.buyer_authorization_id,
            merchant_decision_id=record.merchant_decision_id,
            merchant_id=record.merchant_id,
            buyer_id=record.buyer_id,
            amount_minor=record.amount_minor,
            currency=record.currency,
            state=TransactionState(record.state),
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
        )


def deep_mutable_copy(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return a JSON-column-friendly copy of an immutable event metadata snapshot."""

    return {key: _to_mutable(item) for key, item in value.items()}


def _to_mutable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _to_mutable(item) for key, item in value.items()}
    if isinstance(value, tuple | frozenset):
        return [_to_mutable(item) for item in value]
    return value


def _as_utc(value: datetime) -> datetime:
    """Normalize DB timestamps; SQLite drops timezone data in portable tests."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
