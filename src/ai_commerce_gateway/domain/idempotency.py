"""Domain types and fingerprint logic for catalog-mutation idempotency.

Mirrors the transaction-lane ``execution.py`` pattern: a frozen record,
a deterministic request fingerprint, and a strict same-fingerprint replay
rule.  The backing table is the shared ``idempotency_records`` table.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from ai_commerce_gateway.core.errors import AppError, ErrorCode

# ---------------------------------------------------------------------------
# Operation constants
# ---------------------------------------------------------------------------

CATALOG_CREATE_PRODUCT: Final = "catalog.create_product"
CATALOG_UPDATE_PRODUCT: Final = "catalog.update_product"
CATALOG_PUBLISH_PRODUCT: Final = "catalog.publish_product"
CATALOG_UNPUBLISH_PRODUCT: Final = "catalog.unpublish_product"

CATALOG_IDEMPOTENT_OPERATIONS: Final[frozenset[str]] = frozenset(
    {
        CATALOG_CREATE_PRODUCT,
        CATALOG_UPDATE_PRODUCT,
        CATALOG_PUBLISH_PRODUCT,
        CATALOG_UNPUBLISH_PRODUCT,
    }
)


# ---------------------------------------------------------------------------
# Fingerprint helpers
# ---------------------------------------------------------------------------

def _hash_payload(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def catalog_request_fingerprint(
    *,
    actor_id: str,
    operation: str,
    merchant_id: str,
    product_id: str = "",
    idempotency_key: str,
    **fields: object,
) -> str:
    """Deterministic SHA-256 fingerprint for a catalog mutation request.

    The fingerprint encodes the actor, operation, tenant, resource identity
    and the caller-supplied idempotency key together with any extra
    mutation-relevant fields (title, price, expected_version, etc.).
    Two requests with the same logical intent MUST produce the same
    fingerprint; two requests with different intent MUST NOT.
    """
    payload: dict[str, object] = {
        "actor_id": actor_id,
        "operation": operation,
        "merchant_id": merchant_id,
        "product_id": product_id,
        "idempotency_key": idempotency_key,
    }
    if fields:
        payload["fields"] = fields
    return _hash_payload(payload)


def response_fingerprint(response_json: str) -> str:
    """Hash of the serialised response body for replay verification."""
    return f"sha256:{hashlib.sha256(response_json.encode()).hexdigest()}"


# ---------------------------------------------------------------------------
# Idempotency record
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CatalogIdempotencyRecord:
    """Immutable snapshot of a catalog idempotency record."""

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
        if self.created_at.tzinfo is None or self.created_at.utcoffset() != UTC.utcoffset(
            self.created_at
        ):
            raise ValueError("created_at must be timezone-aware UTC")

    def require_same_request(self, request_fingerprint: str) -> None:
        """Raise if the supplied fingerprint does not match this record's."""
        if self.request_fingerprint != request_fingerprint:
            raise AppError(
                ErrorCode.IDEMPOTENCY_KEY_REUSED,
                "Idempotency key was already used for another request.",
                status_code=409,
            )
