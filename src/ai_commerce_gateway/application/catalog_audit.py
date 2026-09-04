"""Structured merchant/catalog audit events (P0-7).

Emits one structured JSON log record per catalog mutation with actor,
action, tenant, target, correlation ID, causation reference, timestamp and
before/after version/state where applicable.

Hard rule (SECURITY.md): no secrets, LLM API keys, confirmation tokens or
raw sensitive payloads ever appear in these events.  The field set is
allowlisted by construction — only operational identifiers and states.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Final

AUDIT_LOGGER_NAME: Final[str] = "ai_commerce_gateway.catalog_audit"

audit_logger = logging.getLogger(AUDIT_LOGGER_NAME)


@dataclass(frozen=True, slots=True)
class CatalogAuditEvent:
    """A structured, secret-free catalog audit event."""

    actor_id: str
    actor_type: str
    action: str
    merchant_id: str
    target_type: str
    target_id: str
    correlation_id: str
    causation: str | None  # e.g. idempotency key / confirmation jti
    before: dict[str, object] | None
    after: dict[str, object] | None
    version_before: int | None
    version_after: int | None
    occurred_at: datetime


def emit_catalog_audit(event: CatalogAuditEvent) -> None:
    """Emit a catalog audit event as a single structured JSON log record.

    Only the allowlisted operational fields are serialised; nothing else can
    leak because the event type carries nothing else.
    """
    record = {
        "event": "catalog.audit",
        "actor_id": event.actor_id,
        "actor_type": event.actor_type,
        "action": event.action,
        "merchant_id": event.merchant_id,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "correlation_id": event.correlation_id,
        "causation": event.causation,
        "before": event.before,
        "after": event.after,
        "version_before": event.version_before,
        "version_after": event.version_after,
        "occurred_at": event.occurred_at.isoformat(),
    }
    audit_logger.info(json.dumps(record, sort_keys=True, default=str))


def product_snapshot(view: object) -> dict[str, object]:
    """Minimal, safe product state for audit diffs (no description blobs)."""
    status = getattr(view, "status", None)
    return {
        "status": getattr(status, "value", status),
        "price_minor": getattr(getattr(view, "price", None), "amount_minor", None),
        "currency": getattr(getattr(view, "price", None), "currency", None),
        "available_quantity": getattr(view, "available_quantity", None),
    }
