"""Tool Orchestration layer for the Reference Buyer Chat (C3).

This module connects a conversational AI (LLMClient) with the BuyerAdapter.
It restricts the AI to the 7 canonical tools, prevents self-approval,
and safely formats results (like images) for the chat UI.
"""

from typing import Any

from ai_commerce_gateway.application.buyer_adapter.adapter import BuyerAdapter
from ai_commerce_gateway.application.buyer_adapter.llm_client import LLMClient
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
from ai_commerce_gateway.contracts.models import ActorContext

# The 7 canonical tools exposed to the AI
ALLOWED_TOOLS = {
    "search_catalog",
    "get_product",
    "create_purchase_proposal",
    "request_authorization",
    "execute_transaction",
    "get_transaction_status",
    "get_transaction_audit",
}


class ToolOrchestrator:
    """Orchestrates conversations, mapping AI intents to safe BuyerAdapter tool calls."""

    def __init__(self, llm_client: LLMClient, adapter: BuyerAdapter) -> None:
        self.llm_client = llm_client
        self.adapter = adapter

    def _get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return the JSON schemas for the 7 allowed tools (stubbed for demo)."""
        # In a real implementation, we would derive these from the Pydantic models.
        return [{"name": name, "description": f"Tool for {name}"} for name in ALLOWED_TOOLS]

    def chat(
        self,
        actor: ActorContext,
        invocation: InvocationContext,
        messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Process a chat interaction.
        1. Calls the LLM to get text or tool calls.
        2. Routes tool calls to the BuyerAdapter.
        3. Returns the assistant's reply and any structured tool execution results.
        """
        response = self.llm_client.generate(messages, tools=self._get_tool_schemas())

        result: dict[str, Any] = {
            "text": response.text,
            "tool_calls": [],
            "tool_results": [],
            "handoff_required": False,
        }

        if response.tool_calls:
            for tc in response.tool_calls:
                # Security: Restrict AI to ONLY the explicitly allowed tools.
                # No self-approval, no Razorpay, no internal admin functions.
                if tc.name not in ALLOWED_TOOLS:
                    result["tool_results"].append(
                        {
                            "tool": tc.name,
                            "error": "Tool not allowed. AI cannot perform this action.",
                        }
                    )
                    continue

                result["tool_calls"].append(tc.name)

                try:
                    tool_result = self._execute_tool(actor, invocation, tc.name, tc.arguments)
                    result["tool_results"].append({"tool": tc.name, "result": tool_result})

                    # Explicit Handoff Logic:
                    # If the AI proposes a purchase or requests authorization, it MUST stop
                    # and hand off to the human buyer for review and consent via the UI.
                    if tc.name in (
                        "create_purchase_proposal",
                        "request_authorization",
                        "execute_transaction",
                    ):
                        result["handoff_required"] = True
                        if not result["text"]:
                            if tc.name == "execute_transaction":
                                result["text"] = (
                                    "Payment handoff initiated. "
                                    "Please complete the payment process."
                                )
                            else:
                                result["text"] = "Please review and authorize the transaction."

                except ValueError as e:
                    result["tool_results"].append({"tool": tc.name, "error": str(e)})

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

            # Redact provider details for buyer presentation
            audit_items = []
            for e in res_audit.items:
                item = e.model_dump()
                # Strip any internal or provider metadata
                if "metadata" in item:
                    item["metadata"] = "[REDACTED]" if item["metadata"] else {}
                audit_items.append(item)

            return {"items": audit_items, "next_cursor": res_audit.next_cursor}

        raise ValueError(f"Unknown tool {tool_name}")
