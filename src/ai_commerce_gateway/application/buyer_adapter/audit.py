"""Non-sensitive AI orchestration audit events (P0-2).

Every consequential step the buyer AI takes is recorded as a structured audit
event. Events intentionally contain ONLY non-sensitive fields:

    request_id        transport request identifier
    correlation_id    request correlation identifier
    actor_id          authenticated buyer identifier
    turn              bounded loop turn number
    tool              tool name requested
    outcome           requested | completed | rejected | failed
    result_reference  stable reference to the tool result (proposal/transaction/
                      product id, or a non-sensitive summary), never payload data

Raw prompts, free-text arguments and tool payloads are NEVER stored. The chat
response returns the same events to the buyer UI as the "AI works" trace.
"""

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Final, Protocol

logger = logging.getLogger(__name__)

OUTCOME_REQUESTED: Final[str] = "requested"
OUTCOME_COMPLETED: Final[str] = "completed"
OUTCOME_REJECTED: Final[str] = "rejected"
OUTCOME_FAILED: Final[str] = "failed"


@dataclass(frozen=True, slots=True)
class AiOrchestrationAuditEvent:
    """One non-sensitive AI orchestration step."""

    request_id: str
    correlation_id: str
    actor_id: str
    turn: int
    tool: str
    outcome: str
    result_reference: str | None
    created_at: datetime


class AiOrchestrationAuditRecorder(Protocol):
    """Recording port for AI orchestration audit events."""

    def record(self, event: AiOrchestrationAuditEvent) -> None: ...


class LoggingAiOrchestrationAuditRecorder:
    """Default recorder: emits structured, non-sensitive log records.

    A durable implementation (database-backed) can be injected through the
    orchestrator constructor when the audit store is provisioned.
    """

    def record(self, event: AiOrchestrationAuditEvent) -> None:
        logger.info(
            "ai_orchestration_audit request_id=%s correlation_id=%s actor_id=%s "
            "turn=%d tool=%s outcome=%s result_reference=%s created_at=%s",
            event.request_id,
            event.correlation_id,
            event.actor_id,
            event.turn,
            event.tool,
            event.outcome,
            event.result_reference,
            event.created_at.isoformat(),
        )


def make_event(
    *,
    request_id: str,
    correlation_id: str,
    actor_id: str,
    turn: int,
    tool: str,
    outcome: str,
    result_reference: str | None = None,
) -> AiOrchestrationAuditEvent:
    return AiOrchestrationAuditEvent(
        request_id=request_id,
        correlation_id=correlation_id,
        actor_id=actor_id,
        turn=turn,
        tool=tool,
        outcome=outcome,
        result_reference=result_reference,
        created_at=datetime.now(UTC),
    )


def event_to_dict(event: AiOrchestrationAuditEvent) -> dict[str, Any]:
    """Serialize for the chat response trace (non-sensitive fields only)."""
    payload = asdict(event)
    payload["created_at"] = event.created_at.isoformat()
    return payload


def extract_result_reference(tool: str, result: Any) -> str | None:
    """Derive a stable, non-sensitive reference to a tool result.

    Only identifiers and coarse counts are extracted — never free-text
    content from the payload.
    """
    if not isinstance(result, dict):
        return None
    for key in ("id", "transaction_id", "proposal_id"):
        value = result.get(key)
        if isinstance(value, str) and value:
            return value
    items = result.get("items")
    if isinstance(items, list):
        return f"{tool}_items:{len(items)}"
    state = result.get("raw_state") or result.get("state")
    if isinstance(state, str) and state:
        return f"{tool}:{state}"
    return None
