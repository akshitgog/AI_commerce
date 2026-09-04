import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ProviderName
from ai_commerce_gateway.domain.transactions import Transaction

EXECUTE_TRANSACTION_OPERATION: Final = "transaction.execute"


def _hash_payload(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def execution_request_fingerprint(*, actor_id: str, transaction_id: str) -> str:
    return _hash_payload(
        {
            "actor_id": actor_id,
            "operation": EXECUTE_TRANSACTION_OPERATION,
            "transaction_id": transaction_id,
        }
    )


def provider_request_fingerprint(transaction: Transaction, provider: ProviderName) -> str:
    return _hash_payload(
        {
            "amount_minor": transaction.amount_minor,
            "currency": transaction.currency,
            "provider": provider.value,
            "transaction_id": transaction.id,
        }
    )


def response_fingerprint(response_json: str) -> str:
    return f"sha256:{hashlib.sha256(response_json.encode()).hexdigest()}"


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    id: str
    actor_id: str
    operation: str
    idempotency_key: str
    request_fingerprint: str
    resource_type: str | None
    resource_id: str | None
    response_code: int | None
    response_body_hash: str | None
    created_at: datetime

    def __post_init__(self) -> None:
        for field_name in (
            "id",
            "actor_id",
            "operation",
            "idempotency_key",
            "request_fingerprint",
        ):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")
        _require_utc(self.created_at, "created_at")

    def require_same_request(self, request_fingerprint: str) -> None:
        if self.request_fingerprint != request_fingerprint:
            raise AppError(
                ErrorCode.IDEMPOTENCY_KEY_REUSED,
                "Idempotency key was already used for another request.",
                status_code=409,
            )


@dataclass(frozen=True, slots=True)
class PaymentAttempt:
    id: str
    transaction_id: str
    attempt_number: int
    provider: ProviderName
    provider_request_fingerprint: str
    provider_order_id: str | None
    provider_payment_id: str | None
    provider_order_state: str | None
    provider_payment_state: str | None
    capture_state: str | None
    last_verified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.attempt_number < 1:
            raise ValueError("attempt number must be positive")
        _require_utc(self.created_at, "created_at")
        _require_utc(self.updated_at, "updated_at")
        if self.last_verified_at is not None:
            _require_utc(self.last_verified_at, "last_verified_at")


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
