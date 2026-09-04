import json
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Final

from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.core.ids import new_id
from ai_commerce_gateway.domain.enums import ActorType, TransactionState

STATE_CHANGED_EVENT_TYPE: Final = "TRANSACTION_STATE_CHANGED"

_PRE_DISPATCH_STATES: Final = frozenset(
    {
        TransactionState.PROPOSED,
        TransactionState.BUYER_AUTH_REQUIRED,
        TransactionState.MERCHANT_POLICY_PENDING,
        TransactionState.MERCHANT_REVIEW_REQUIRED,
        TransactionState.READY,
    }
)

_BASE_TRANSITIONS: Final[dict[TransactionState, frozenset[TransactionState]]] = {
    TransactionState.PROPOSED: frozenset(
        {
            TransactionState.BUYER_AUTH_REQUIRED,
            TransactionState.MERCHANT_POLICY_PENDING,
        }
    ),
    TransactionState.BUYER_AUTH_REQUIRED: frozenset({TransactionState.MERCHANT_POLICY_PENDING}),
    TransactionState.MERCHANT_POLICY_PENDING: frozenset(
        {
            TransactionState.MERCHANT_REVIEW_REQUIRED,
            TransactionState.READY,
            TransactionState.FAILED,
        }
    ),
    TransactionState.MERCHANT_REVIEW_REQUIRED: frozenset(
        {TransactionState.READY, TransactionState.FAILED}
    ),
    TransactionState.READY: frozenset({TransactionState.EXECUTING}),
    TransactionState.EXECUTING: frozenset(
        {TransactionState.PAYMENT_PENDING, TransactionState.UNKNOWN}
    ),
    TransactionState.PAYMENT_PENDING: frozenset({TransactionState.VERIFYING}),
    TransactionState.VERIFYING: frozenset({TransactionState.SUCCEEDED, TransactionState.FAILED}),
    TransactionState.UNKNOWN: frozenset({TransactionState.RECONCILING}),
    TransactionState.RECONCILING: frozenset(
        {
            TransactionState.PAYMENT_PENDING,
            TransactionState.SUCCEEDED,
            TransactionState.FAILED,
        }
    ),
    TransactionState.SUCCEEDED: frozenset(),
    TransactionState.FAILED: frozenset(),
    TransactionState.CANCELLED: frozenset(),
    TransactionState.EXPIRED: frozenset(),
}

ALLOWED_TRANSITIONS: Final[Mapping[TransactionState, frozenset[TransactionState]]] = (
    MappingProxyType(
        {
            state: targets | {TransactionState.CANCELLED, TransactionState.EXPIRED}
            if state in _PRE_DISPATCH_STATES
            else targets
            for state, targets in _BASE_TRANSITIONS.items()
        }
    )
)


class InvalidTransactionTransition(AppError):
    def __init__(self, previous_state: TransactionState, new_state: TransactionState) -> None:
        super().__init__(
            ErrorCode.INVALID_STATE,
            f"Transaction cannot transition from {previous_state} to {new_state}.",
            status_code=409,
            details={
                "previous_state": previous_state.value,
                "new_state": new_state.value,
            },
        )
        self.previous_state = previous_state
        self.new_state = new_state


def _require_non_empty(value: str, field_name: str) -> None:
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class TransactionEvent:
    id: str
    transaction_id: str
    event_type: str
    actor_type: ActorType
    actor_id: str | None
    reason_code: str
    previous_state: TransactionState
    new_state: TransactionState
    correlation_id: str
    provider_reference_redacted: str | None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        _require_non_empty(self.id, "id")
        _require_non_empty(self.transaction_id, "transaction_id")
        _require_non_empty(self.event_type, "event_type")
        _require_non_empty(self.reason_code, "reason_code")
        _require_non_empty(self.correlation_id, "correlation_id")
        _require_utc(self.created_at, "created_at")
        if self.actor_type in {ActorType.BUYER, ActorType.MERCHANT_USER} and not self.actor_id:
            raise ValueError(f"actor_id is required for {self.actor_type}")
        try:
            metadata_copy = json.loads(json.dumps(dict(self.metadata)))
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata must contain only JSON-compatible values") from exc
        object.__setattr__(self, "metadata", _freeze_json(metadata_copy))


@dataclass(frozen=True, slots=True)
class TransactionTransition:
    transaction: "Transaction"
    event: TransactionEvent


@dataclass(frozen=True, slots=True)
class Transaction:
    id: str
    proposal_id: str
    buyer_authorization_id: str | None
    merchant_decision_id: str | None
    merchant_id: str
    buyer_id: str
    amount_minor: int
    currency: str
    state: TransactionState
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        for field_name in ("id", "proposal_id", "merchant_id", "buyer_id"):
            _require_non_empty(getattr(self, field_name), field_name)
        if isinstance(self.amount_minor, bool) or not isinstance(self.amount_minor, int):
            raise TypeError("amount_minor must be an integer")
        if self.amount_minor < 0:
            raise ValueError("amount_minor must be non-negative")
        if (
            len(self.currency) != 3
            or not self.currency.isascii()
            or not self.currency.isalpha()
            or not self.currency.isupper()
        ):
            raise ValueError("currency must be a three-letter uppercase code")
        _require_utc(self.created_at, "created_at")
        _require_utc(self.updated_at, "updated_at")

    def transition(
        self,
        new_state: TransactionState,
        *,
        actor_type: ActorType,
        actor_id: str | None,
        reason_code: str,
        correlation_id: str,
        provider_reference_redacted: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        event_id: str | None = None,
        occurred_at: datetime | None = None,
    ) -> TransactionTransition:
        if new_state not in ALLOWED_TRANSITIONS[self.state]:
            raise InvalidTransactionTransition(self.state, new_state)

        transition_time = occurred_at or datetime.now(UTC)
        event = TransactionEvent(
            id=event_id or new_id("tevt"),
            transaction_id=self.id,
            event_type=STATE_CHANGED_EVENT_TYPE,
            actor_type=actor_type,
            actor_id=actor_id,
            reason_code=reason_code,
            previous_state=self.state,
            new_state=new_state,
            correlation_id=correlation_id,
            provider_reference_redacted=provider_reference_redacted,
            metadata=metadata or {},
            created_at=transition_time,
        )
        return TransactionTransition(
            transaction=replace(self, state=new_state, updated_at=transition_time),
            event=event,
        )


def allowed_transitions_from(state: TransactionState) -> frozenset[TransactionState]:
    return ALLOWED_TRANSITIONS[state]
