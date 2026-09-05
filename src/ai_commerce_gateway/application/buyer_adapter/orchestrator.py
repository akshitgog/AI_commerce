"""Bounded Buyer AI orchestration (P0-2).

Connects the configured LLM client to the BuyerAdapter inside a bounded
tool-result loop:

    intent → search → inspect/compare → proposal → HUMAN authorization
    handoff → transaction status

Hard guarantees enforced here:

* The model only ever sees the 7 canonical tools with their COMPLETE JSON
  schemas (``tools.ALL_TOOLS``). There is no tool to set price, approve an
  authorization, set transaction state, call the provider, or bypass policy.
* A handoff tool result (proposal / authorization / execute) stops the loop
  immediately; any further tool calls from the same model response are
  dropped so the AI can never chain past the human authorization gate.
* The loop is hard-bounded by ``max_tool_steps`` from configuration.
* Every tool step records a non-sensitive orchestration audit event
  (request/correlation ID, tool requested, result reference, outcome).
  Raw prompts and free-text arguments are never stored.
"""

from typing import Any, Final

from ai_commerce_gateway.application.buyer_adapter.adapter import BuyerAdapter
from ai_commerce_gateway.application.buyer_adapter.audit import (
    OUTCOME_COMPLETED,
    OUTCOME_FAILED,
    OUTCOME_REJECTED,
    OUTCOME_REQUESTED,
    AiOrchestrationAuditEvent,
    AiOrchestrationAuditRecorder,
    LoggingAiOrchestrationAuditRecorder,
    event_to_dict,
    extract_result_reference,
    make_event,
)
from ai_commerce_gateway.application.buyer_adapter.llm_client import LLMClient, ToolCall
from ai_commerce_gateway.application.buyer_adapter.schemas import (
    CreatePurchaseProposalRequest,
    ExecuteTransactionRequest,
    GetProductRequest,
    GetTransactionAuditRequest,
    GetTransactionStatusRequest,
    InvocationContext,
    RequestAuthorizationRequest,
    SearchCatalogRequest,
)
from ai_commerce_gateway.application.buyer_adapter.tools import ALL_TOOLS
from ai_commerce_gateway.contracts.models import ActorContext

# The 7 canonical tools exposed to the AI
ALLOWED_TOOLS: Final[frozenset[str]] = frozenset(
    {
        "search_catalog",
        "get_product",
        "create_purchase_proposal",
        "request_authorization",
        "execute_transaction",
        "get_transaction_status",
        "get_transaction_audit",
    }
)

#: Tools whose successful result hands the conversation to the human buyer.
HANDOFF_TOOLS: Final[frozenset[str]] = frozenset(
    {
        "create_purchase_proposal",
        "request_authorization",
        "execute_transaction",
    }
)

_STEP_LIMIT_MESSAGE: Final[str] = (
    "I reached the maximum number of steps for this request. "
    "Please review the results above and tell me how to proceed."
)


class ToolOrchestrator:
    """Orchestrates conversations, mapping AI intents to safe BuyerAdapter tool calls."""

    def __init__(
        self,
        llm_client: LLMClient,
        adapter: BuyerAdapter,
        *,
        auditor: AiOrchestrationAuditRecorder | None = None,
        max_tool_steps: int = 8,
    ) -> None:
        if max_tool_steps < 1:
            raise ValueError("max_tool_steps must be >= 1")
        self.llm_client = llm_client
        self.adapter = adapter
        self.auditor = auditor or LoggingAiOrchestrationAuditRecorder()
        self.max_tool_steps = max_tool_steps

    def _get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return the complete JSON schemas for the bounded tool surface."""
        return [dict(tool) for tool in ALL_TOOLS]

    def _record(self, event: AiOrchestrationAuditEvent) -> None:
        self.auditor.record(event)

    def chat(
        self,
        actor: ActorContext,
        invocation: InvocationContext,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Process a chat interaction inside a bounded tool-result loop.

        1. Calls the LLM with the conversation so far and the bounded tools.
        2. Executes requested tool calls against the BuyerAdapter.
        3. Feeds results back to the model until it replies with text,
           a handoff is reached, or the step bound is hit.
        """

        conversation = list(messages)
        audit_events: list[AiOrchestrationAuditEvent] = []
        request_id = invocation.request_id or "unknown"
        correlation_id = invocation.correlation_id

        result: dict[str, Any] = {
            "text": None,
            "tool_calls": [],
            "tool_results": [],
            "handoff_required": False,
            "trace": [],
        }

        def record(
            *,
            turn: int,
            tool: str,
            outcome: str,
            result_reference: str | None = None,
        ) -> None:
            event = make_event(
                request_id=request_id,
                correlation_id=correlation_id,
                actor_id=actor.actor_id,
                turn=turn,
                tool=tool,
                outcome=outcome,
                result_reference=result_reference,
            )
            self._record(event)
            audit_events.append(event)

        for turn in range(self.max_tool_steps):
            response = self.llm_client.generate(conversation, tools=self._get_tool_schemas())
            if response.text:
                result["text"] = response.text

            if not response.tool_calls:
                break

            conversation.append(_assistant_tool_call_message(response.tool_calls, response.text))

            hit_handoff = False
            for index, tool_call in enumerate(response.tool_calls):
                if hit_handoff:
                    # Hard gate: a successful handoff result ends AI action for
                    # this turn. Any further calls the model requested are
                    # dropped so the AI can never chain past human review.
                    record(
                        turn=turn,
                        tool=tool_call.name,
                        outcome=OUTCOME_REJECTED,
                        result_reference="dropped-after-handoff",
                    )
                    result["tool_results"].append(
                        {
                            "tool": tool_call.name,
                            "error": (
                                "Pending human authorization handoff; this step was not executed."
                            ),
                        }
                    )
                    continue

                record(
                    turn=turn,
                    tool=tool_call.name,
                    outcome=OUTCOME_REQUESTED,
                )

                if tool_call.name not in ALLOWED_TOOLS:
                    record(
                        turn=turn,
                        tool=tool_call.name,
                        outcome=OUTCOME_REJECTED,
                        result_reference="tool-not-allowed",
                    )
                    error = "Tool not allowed. AI cannot perform this action."
                    result["tool_results"].append({"tool": tool_call.name, "error": error})
                    conversation.append(_tool_result_message(tool_call, index, {"error": error}))
                    continue

                result["tool_calls"].append(tool_call.name)

                try:
                    tool_result = self._execute_tool(
                        actor, invocation, tool_call.name, tool_call.arguments
                    )
                except ValueError as exc:
                    record(
                        turn=turn,
                        tool=tool_call.name,
                        outcome=OUTCOME_FAILED,
                        result_reference=str(exc)[:200],
                    )
                    result["tool_results"].append({"tool": tool_call.name, "error": str(exc)})
                    conversation.append(_tool_result_message(tool_call, index, {"error": str(exc)}))
                    continue

                record(
                    turn=turn,
                    tool=tool_call.name,
                    outcome=OUTCOME_COMPLETED,
                    result_reference=extract_result_reference(tool_call.name, tool_result),
                )
                result["tool_results"].append({"tool": tool_call.name, "result": tool_result})
                conversation.append(_tool_result_message(tool_call, index, tool_result))

                if tool_call.name in HANDOFF_TOOLS:
                    hit_handoff = True
                    result["handoff_required"] = True
                    if not result["text"]:
                        if tool_call.name == "execute_transaction":
                            result["text"] = (
                                "Payment handoff initiated. Please complete the payment process."
                            )
                        else:
                            result["text"] = "Please review and authorize the transaction."

            if hit_handoff:
                break
        else:
            if not result["text"]:
                result["text"] = _STEP_LIMIT_MESSAGE

        result["trace"] = [event_to_dict(event) for event in audit_events]
        return result

    def _execute_tool(
        self,
        actor: ActorContext,
        invocation: InvocationContext,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Dispatch a validated tool call to the BuyerAdapter."""

        # Pydantic strictly validates all incoming arguments against the schemas.
        # This prevents the AI from injecting extra fields like `price` or `total`.

        if tool_name == "search_catalog":
            req_search = SearchCatalogRequest(**arguments)
            res_search = self.adapter.search_catalog(actor, invocation, req_search)
            # Safe rendering wrapper: ensure images are formatted safely
            items = [p.model_dump() for p in res_search.items]
            return {"items": items, "next_cursor": res_search.next_cursor}

        elif tool_name == "get_product":
            req_product = GetProductRequest(**arguments)
            res_product = self.adapter.get_product(actor, invocation, req_product)
            return res_product.model_dump()

        elif tool_name == "create_purchase_proposal":
            req_proposal = CreatePurchaseProposalRequest(**arguments)
            res_proposal = self.adapter.create_purchase_proposal(actor, invocation, req_proposal)
            return res_proposal.model_dump()

        elif tool_name == "request_authorization":
            req_auth = RequestAuthorizationRequest(**arguments)
            res_auth = self.adapter.request_authorization(actor, invocation, req_auth)
            return res_auth.model_dump()

        elif tool_name == "execute_transaction":
            req_exec = ExecuteTransactionRequest(**arguments)
            res_exec = self.adapter.execute_transaction(actor, invocation, req_exec)
            return res_exec.model_dump()

        elif tool_name == "get_transaction_status":
            req_status = GetTransactionStatusRequest(**arguments)
            res_status = self.adapter.get_transaction_status(actor, invocation, req_status)

            # Map raw status to buyer-safe presentation
            presentation_status = res_status.state.value
            recovery_instructions = None

            if res_status.state.value == "FAILED":
                presentation_status = "Payment failed"
                recovery_instructions = (
                    "Please try a different payment method or request a new proposal."
                )
            elif res_status.state.value == "SUCCEEDED":
                presentation_status = "Payment successful"
            elif res_status.state.value in ("EXECUTING", "PAYMENT_PENDING", "VERIFYING"):
                presentation_status = "Processing payment"
            elif res_status.state.value in ("UNKNOWN", "RECONCILING"):
                presentation_status = "Payment status uncertain"
                recovery_instructions = (
                    "Payment status is uncertain — we're reconciling automatically; "
                    "no action needed."
                )

            return {
                "transaction_id": res_status.id,
                "proposal_id": res_status.proposal_id,
                "amount": res_status.amount.model_dump(),
                "state": presentation_status,
                "raw_state": res_status.state.value,
                "recovery_instructions": recovery_instructions,
            }

        elif tool_name == "get_transaction_audit":
            req_audit = GetTransactionAuditRequest(**arguments)
            res_audit = self.adapter.get_transaction_audit(actor, invocation, req_audit)

            # Metadata was already allowlist-redacted at the adapter
            # (SECURITY.md strict allowlist, see adapter._redact_event);
            # present the compliant events as-is.
            audit_items = [e.model_dump() for e in res_audit.items]

            return {"items": audit_items, "next_cursor": res_audit.next_cursor}

        raise ValueError(f"Unknown tool {tool_name}")


def _assistant_tool_call_message(tool_calls: list[ToolCall], text: str | None) -> dict[str, Any]:
    """Build the assistant message that precedes tool results in the loop."""
    return {
        "role": "assistant",
        "content": text,
        "tool_calls": [
            {
                "id": tool_call.id or f"call_{index}",
                "type": "function",
                "function": {"name": tool_call.name, "arguments": tool_call.arguments},
            }
            for index, tool_call in enumerate(tool_calls)
        ],
    }


def _tool_result_message(
    tool_call: ToolCall, index: int, payload: dict[str, Any]
) -> dict[str, Any]:
    """Build the tool-result message fed back to the model.

    Only the tool result itself is included; the conversation loop never
    stores raw user prompts in the audit trail (see audit.py).
    """
    import json

    return {
        "role": "tool",
        "tool_call_id": tool_call.id or f"call_{index}",
        "name": tool_call.name,
        "content": json.dumps(payload, default=str),
    }
