from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta

import pytest

from ai_commerce_gateway.core.errors import ErrorCode
from ai_commerce_gateway.domain.enums import ActorType, TransactionState
from ai_commerce_gateway.domain.transactions import (
    ALLOWED_TRANSITIONS,
    STATE_CHANGED_EVENT_TYPE,
    InvalidTransactionTransition,
    Transaction,
    allowed_transitions_from,
)

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def make_transaction(
    state: TransactionState = TransactionState.PROPOSED,
    *,
    amount_minor: int = 50_000,
    currency: str = "INR",
) -> Transaction:
    return Transaction(
        id="txn_test",
        proposal_id="prop_test",
        buyer_authorization_id="auth_test",
        merchant_decision_id="mdec_test",
        merchant_id="mer_test",
        buyer_id="buy_test",
        amount_minor=amount_minor,
        currency=currency,
        state=state,
        created_at=NOW,
        updated_at=NOW,
    )


EXPECTED_TRANSITIONS = {
    TransactionState.PROPOSED: {
        TransactionState.BUYER_AUTH_REQUIRED,
        TransactionState.MERCHANT_POLICY_PENDING,
        TransactionState.CANCELLED,
        TransactionState.EXPIRED,
    },
    TransactionState.BUYER_AUTH_REQUIRED: {
        TransactionState.MERCHANT_POLICY_PENDING,
        TransactionState.CANCELLED,
        TransactionState.EXPIRED,
    },
    TransactionState.MERCHANT_POLICY_PENDING: {
        TransactionState.MERCHANT_REVIEW_REQUIRED,
        TransactionState.READY,
        TransactionState.FAILED,
        TransactionState.CANCELLED,
        TransactionState.EXPIRED,
    },
    TransactionState.MERCHANT_REVIEW_REQUIRED: {
        TransactionState.READY,
        TransactionState.FAILED,
        TransactionState.CANCELLED,
        TransactionState.EXPIRED,
    },
    TransactionState.READY: {
        TransactionState.EXECUTING,
        TransactionState.CANCELLED,
        TransactionState.EXPIRED,
    },
    TransactionState.EXECUTING: {
        TransactionState.PAYMENT_PENDING,
        TransactionState.UNKNOWN,
        TransactionState.RECONCILING,
    },
    TransactionState.PAYMENT_PENDING: {TransactionState.VERIFYING},
    TransactionState.VERIFYING: {TransactionState.SUCCEEDED, TransactionState.FAILED},
    TransactionState.UNKNOWN: {TransactionState.RECONCILING},
    TransactionState.RECONCILING: {
        TransactionState.PAYMENT_PENDING,
        TransactionState.SUCCEEDED,
        TransactionState.FAILED,
        TransactionState.UNKNOWN,
    },
    TransactionState.SUCCEEDED: set(),
    TransactionState.FAILED: set(),
    TransactionState.CANCELLED: set(),
    TransactionState.EXPIRED: set(),
}


def test_transition_table_exactly_matches_the_canonical_lifecycle() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(TransactionState)
    assert {state: set(targets) for state, targets in ALLOWED_TRANSITIONS.items()} == (
        EXPECTED_TRANSITIONS
    )


@pytest.mark.parametrize(
    ("previous_state", "new_state"),
    [
        (previous_state, new_state)
        for previous_state, targets in EXPECTED_TRANSITIONS.items()
        for new_state in targets
    ],
)
def test_every_canonical_transition_is_accepted(
    previous_state: TransactionState, new_state: TransactionState
) -> None:
    result = make_transaction(previous_state).transition(
        new_state,
        actor_type=ActorType.SYSTEM,
        actor_id=None,
        reason_code="TEST_TRANSITION",
        correlation_id="corr_test",
        occurred_at=NOW + timedelta(seconds=1),
    )
    assert result.transaction.state is new_state


@pytest.mark.parametrize(
    ("previous_state", "new_state"),
    [
        (previous_state, new_state)
        for previous_state in TransactionState
        for new_state in TransactionState
        if new_state not in EXPECTED_TRANSITIONS[previous_state]
    ],
)
def test_every_noncanonical_transition_is_rejected(
    previous_state: TransactionState, new_state: TransactionState
) -> None:
    with pytest.raises(InvalidTransactionTransition) as error:
        make_transaction(previous_state).transition(
            new_state,
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            reason_code="TEST_TRANSITION",
            correlation_id="corr_test",
        )
    assert error.value.code is ErrorCode.INVALID_STATE
    assert error.value.details == {
        "previous_state": previous_state.value,
        "new_state": new_state.value,
    }


@pytest.mark.parametrize(
    "terminal_state",
    [
        TransactionState.SUCCEEDED,
        TransactionState.FAILED,
        TransactionState.CANCELLED,
        TransactionState.EXPIRED,
    ],
)
def test_terminal_states_have_no_outgoing_transitions(terminal_state: TransactionState) -> None:
    assert allowed_transitions_from(terminal_state) == frozenset()


@pytest.mark.parametrize(
    "state",
    [
        TransactionState.PROPOSED,
        TransactionState.BUYER_AUTH_REQUIRED,
        TransactionState.MERCHANT_POLICY_PENDING,
        TransactionState.MERCHANT_REVIEW_REQUIRED,
        TransactionState.READY,
    ],
)
@pytest.mark.parametrize("terminal_state", [TransactionState.CANCELLED, TransactionState.EXPIRED])
def test_cancellation_and_expiry_are_limited_to_pre_dispatch_states(
    state: TransactionState, terminal_state: TransactionState
) -> None:
    assert terminal_state in allowed_transitions_from(state)


@pytest.mark.parametrize(
    "state",
    [
        TransactionState.EXECUTING,
        TransactionState.PAYMENT_PENDING,
        TransactionState.VERIFYING,
        TransactionState.UNKNOWN,
        TransactionState.RECONCILING,
    ],
)
@pytest.mark.parametrize("terminal_state", [TransactionState.CANCELLED, TransactionState.EXPIRED])
def test_provider_in_flight_states_cannot_be_cancelled_or_expired(
    state: TransactionState, terminal_state: TransactionState
) -> None:
    assert terminal_state not in allowed_transitions_from(state)


def test_success_requires_the_verification_or_reconciliation_path() -> None:
    assert TransactionState.SUCCEEDED not in allowed_transitions_from(TransactionState.READY)
    assert TransactionState.SUCCEEDED not in allowed_transitions_from(TransactionState.EXECUTING)
    assert TransactionState.SUCCEEDED not in allowed_transitions_from(
        TransactionState.PAYMENT_PENDING
    )
    assert TransactionState.SUCCEEDED in allowed_transitions_from(TransactionState.VERIFYING)
    assert TransactionState.SUCCEEDED in allowed_transitions_from(TransactionState.RECONCILING)


def test_transition_returns_an_immutable_transaction_and_causal_event() -> None:
    source = make_transaction(TransactionState.READY)
    metadata = {"gate": {"buyer": "approved"}, "checks": ["buyer", "merchant"]}
    result = source.transition(
        TransactionState.EXECUTING,
        actor_type=ActorType.BUYER,
        actor_id="buy_test",
        reason_code="EXECUTION_REQUESTED",
        correlation_id="corr_test",
        metadata=metadata,
        event_id="tevt_test",
        occurred_at=NOW + timedelta(seconds=1),
    )

    assert source.state is TransactionState.READY
    assert result.transaction.state is TransactionState.EXECUTING
    assert result.event.event_type == STATE_CHANGED_EVENT_TYPE
    assert result.event.previous_state is TransactionState.READY
    assert result.event.new_state is TransactionState.EXECUTING
    assert result.event.reason_code == "EXECUTION_REQUESTED"
    assert result.event.correlation_id == "corr_test"
    assert result.event.transaction_id == source.id
    metadata["gate"]["buyer"] = "tampered"
    assert result.event.metadata["gate"]["buyer"] == "approved"
    assert result.event.metadata["checks"] == ("buyer", "merchant")

    with pytest.raises(FrozenInstanceError):
        result.transaction.state = TransactionState.SUCCEEDED  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.event.metadata["gate"] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        result.event.metadata["gate"]["buyer"] = "tampered"  # type: ignore[index]


def test_human_actor_types_require_an_actor_id() -> None:
    with pytest.raises(ValueError, match="actor_id is required"):
        make_transaction(TransactionState.READY).transition(
            TransactionState.EXECUTING,
            actor_type=ActorType.BUYER,
            actor_id=None,
            reason_code="EXECUTION_REQUESTED",
            correlation_id="corr_test",
        )


@pytest.mark.parametrize("field_name", ["id", "proposal_id", "merchant_id", "buyer_id"])
def test_transaction_requires_its_binding_identifiers(field_name: str) -> None:
    with pytest.raises(ValueError, match=f"{field_name} must not be empty"):
        replace(make_transaction(), **{field_name: " "})


def test_transaction_timestamps_must_be_utc() -> None:
    with pytest.raises(ValueError, match="updated_at must be timezone-aware UTC"):
        replace(make_transaction(), updated_at=NOW.replace(tzinfo=None))


def test_transition_reason_and_metadata_must_be_auditable() -> None:
    transaction = make_transaction(TransactionState.READY)
    with pytest.raises(ValueError, match="reason_code must not be empty"):
        transaction.transition(
            TransactionState.EXECUTING,
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            reason_code=" ",
            correlation_id="corr_test",
        )
    with pytest.raises(ValueError, match="metadata must contain only JSON-compatible values"):
        transaction.transition(
            TransactionState.EXECUTING,
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            reason_code="EXECUTION_REQUESTED",
            correlation_id="corr_test",
            metadata={"unsupported": object()},
        )


@pytest.mark.parametrize("amount", [1.5, True])
def test_transaction_money_rejects_non_integer_minor_units(amount: object) -> None:
    with pytest.raises(TypeError, match="amount_minor must be an integer"):
        make_transaction(amount_minor=amount)  # type: ignore[call-arg]


def test_transaction_money_rejects_negative_minor_units() -> None:
    with pytest.raises(ValueError, match="amount_minor must be non-negative"):
        make_transaction(amount_minor=-1)


@pytest.mark.parametrize("currency", ["inr", "IN1", "IN", "EURO"])
def test_transaction_currency_is_explicit_and_canonical(currency: str) -> None:
    with pytest.raises(ValueError, match="currency"):
        make_transaction(currency=currency)  # type: ignore[call-arg]
