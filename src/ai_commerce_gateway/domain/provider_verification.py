from dataclasses import dataclass
from datetime import UTC, datetime

from ai_commerce_gateway.contracts.models import Money, ProviderObservation
from ai_commerce_gateway.domain.enums import ProviderName, TransactionState


class ProviderEvidence(ProviderObservation):
    """B5-owned provider evidence without changing the frozen M0 DTO."""

    provider_amount: Money | None = None


@dataclass(frozen=True, slots=True)
class ProviderWebhookReceipt:
    id: str
    provider: ProviderName
    provider_event_id: str
    payload_hash: str
    transaction_id: str | None
    processing_status: str
    received_at: datetime
    processed_at: datetime | None

    def __post_init__(self) -> None:
        for field_name in ("id", "provider_event_id", "payload_hash", "processing_status"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")
        _require_utc(self.received_at, "received_at")
        if self.processed_at is not None:
            _require_utc(self.processed_at, "processed_at")


@dataclass(frozen=True, slots=True)
class WebhookProcessingResult:
    provider_event_id: str
    processing_status: str
    duplicate: bool
    transaction_id: str | None
    transaction_state: TransactionState | None


def webhook_payload_hash(raw_body: bytes) -> str:
    import hashlib

    return f"sha256:{hashlib.sha256(raw_body).hexdigest()}"


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
