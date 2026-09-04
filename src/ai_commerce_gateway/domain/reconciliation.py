"""Reconciliation domain — provider lookup recovery for uncertain transactions.

B6 resolves transactions stuck in UNKNOWN or EXECUTING after a process failure.
It never creates a new provider order or retries dispatch. It only reads provider
truth and applies the canonical state machine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final

from ai_commerce_gateway.domain.enums import TransactionState

# States eligible for reconciliation initiation.
RECONCILABLE_STATES: Final = frozenset({TransactionState.UNKNOWN, TransactionState.EXECUTING})


class ReconciliationOutcome(StrEnum):
    """Result classification after querying provider truth."""

    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    ORDER_CREATED_NO_PAYMENT = "ORDER_CREATED_NO_PAYMENT"
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    PROVIDER_LOOKUP_FAILED = "PROVIDER_LOOKUP_FAILED"


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    """Immutable record of a reconciliation attempt."""

    transaction_id: str
    previous_state: TransactionState
    new_state: TransactionState
    outcome: ReconciliationOutcome
    provider_order_id: str | None
    provider_payment_id: str | None
    resolved_at: datetime

    def __post_init__(self) -> None:
        if not self.transaction_id.strip():
            raise ValueError("transaction_id must not be empty")
        if self.resolved_at.tzinfo is None or self.resolved_at.utcoffset() != UTC.utcoffset(
            self.resolved_at
        ):
            raise ValueError("resolved_at must be timezone-aware UTC")
