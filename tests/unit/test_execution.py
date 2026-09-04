from datetime import UTC, datetime

import pytest

from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ProviderName, TransactionState
from ai_commerce_gateway.domain.execution import (
    IdempotencyRecord,
    PaymentAttempt,
    execution_request_fingerprint,
    provider_request_fingerprint,
    response_fingerprint,
)
from ai_commerce_gateway.domain.transactions import Transaction

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


def transaction() -> Transaction:
    return Transaction(
        id="txn_test",
        proposal_id="prop_test",
        buyer_authorization_id="auth_test",
        merchant_decision_id="mdec_test",
        merchant_id="mer_test",
        buyer_id="buy_test",
        amount_minor=125_00,
        currency="INR",
        state=TransactionState.READY,
        created_at=NOW,
        updated_at=NOW,
    )


def test_execution_fingerprints_are_stable_and_scope_bound() -> None:
    first = execution_request_fingerprint(actor_id="buy_test", transaction_id="txn_test")

    assert first == execution_request_fingerprint(actor_id="buy_test", transaction_id="txn_test")
    assert first != execution_request_fingerprint(actor_id="buy_other", transaction_id="txn_test")
    assert first != execution_request_fingerprint(actor_id="buy_test", transaction_id="txn_other")
    assert provider_request_fingerprint(
        transaction(), ProviderName.RAZORPAY
    ) == provider_request_fingerprint(transaction(), ProviderName.RAZORPAY)
    assert response_fingerprint('{"state":"READY"}') != response_fingerprint(
        '{"state":"EXECUTING"}'
    )


def test_idempotency_record_rejects_a_different_request_fingerprint() -> None:
    record = IdempotencyRecord(
        id="idem_test",
        actor_id="buy_test",
        operation="transaction.execute",
        idempotency_key="key-1",
        request_fingerprint="sha256:first",
        resource_type=None,
        resource_id=None,
        response_code=None,
        response_body_hash=None,
        created_at=NOW,
    )

    record.require_same_request("sha256:first")
    with pytest.raises(AppError) as error:
        record.require_same_request("sha256:second")
    assert error.value.code is ErrorCode.IDEMPOTENCY_KEY_REUSED
    assert error.value.status_code == 409


def test_payment_attempt_requires_a_positive_attempt_number_and_utc_timestamps() -> None:
    values = {
        "id": "pay_test",
        "transaction_id": "txn_test",
        "provider": ProviderName.RAZORPAY,
        "provider_request_fingerprint": "sha256:request",
        "provider_order_id": None,
        "provider_payment_id": None,
        "provider_order_state": None,
        "provider_payment_state": None,
        "capture_state": None,
        "last_verified_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    }

    with pytest.raises(ValueError, match="attempt number"):
        PaymentAttempt(attempt_number=0, **values)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="created_at"):
        PaymentAttempt(
            attempt_number=1,
            **{**values, "created_at": NOW.replace(tzinfo=None)},  # type: ignore[arg-type]
        )
