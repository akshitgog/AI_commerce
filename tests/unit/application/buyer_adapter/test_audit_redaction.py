"""SECURITY.md audit-metadata allowlist enforcement tests.

Verifies that ``BuyerAdapter.get_transaction_audit`` — the single audit
read path shared by the chat orchestrator and the MCP server — strips
every metadata key that is not on the strict allowlist before it reaches
any buyer surface.
"""

from datetime import UTC, datetime
from typing import Any

import pytest

from ai_commerce_gateway.application.buyer_adapter.adapter import (
    AUDIT_METADATA_ALLOWLIST,
    BuyerAdapter,
    _redact_event,
)
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    AuditPage,
    TransactionEventView,
)
from ai_commerce_gateway.domain.enums import ActorType, TransactionState


class FakeTransactionService:
    """Returns a canned AuditPage; mirrors the TransactionService seam."""

    def __init__(self, page: AuditPage) -> None:
        self._page = page

    def get_audit(
        self, transaction_id: str, actor: ActorContext, cursor: str | None = None
    ) -> AuditPage:
        return self._page

    # Unused protocol methods — present for structural conformance.
    def create(self, *args: Any, **kwargs: Any) -> Any: ...
    def execute(self, *args: Any, **kwargs: Any) -> Any: ...
    def get_status(self, *args: Any, **kwargs: Any) -> Any: ...
    def list_for_merchant(self, *args: Any, **kwargs: Any) -> Any: ...
    def reconcile(self, *args: Any, **kwargs: Any) -> Any: ...


def _event(metadata: dict[str, Any]) -> TransactionEventView:
    return TransactionEventView(
        id="evt_1",
        transaction_id="txn_1",
        event_type="STATE_CHANGED",
        actor_type=ActorType.SYSTEM,
        actor_id=None,
        reason_code="PROVIDER_OBSERVATION",
        previous_state=TransactionState.EXECUTING,
        new_state=TransactionState.PAYMENT_PENDING,
        correlation_id="corr_1",
        provider_reference_redacted="...abcd",
        metadata=metadata,
        created_at=datetime.now(tz=UTC),
    )


def _adapter_with_page(page: AuditPage) -> BuyerAdapter:
    return BuyerAdapter(
        catalog=None,  # type: ignore[arg-type]
        proposal=None,  # type: ignore[arg-type]
        auth=None,  # type: ignore[arg-type]
        transaction=FakeTransactionService(page),  # type: ignore[arg-type]
    )


def _actor() -> ActorContext:
    return ActorContext(
        actor_id="buyer_1", actor_type=ActorType.BUYER, correlation_id="corr_1"
    )


def _invocation() -> Any:
    from ai_commerce_gateway.application.buyer_adapter.schemas import InvocationContext

    return InvocationContext(correlation_id="corr_1", request_id="req_1")


def _audit_request() -> Any:
    from ai_commerce_gateway.application.buyer_adapter.schemas import (
        GetTransactionAuditRequest,
    )

    return GetTransactionAuditRequest(transaction_id="txn_1")


class TestRedactEvent:
    def test_allowlisted_metadata_passes_through_unchanged(self):
        event = _event(
            {
                "proposal_id": "prop_1",
                "buyer_id": "buyer_1",
                "merchant_id": "mer_1",
                "attempt_id": "att_1",
                "attempt_number": 1,
                "provider": "razorpay",
                "observation_source": "lookup",
                "authenticity_verified": True,
            }
        )
        redacted = _redact_event(event)
        assert redacted is event  # nothing stripped → same instance
        assert set(redacted.metadata) == {
            "proposal_id",
            "buyer_id",
            "merchant_id",
            "attempt_id",
            "attempt_number",
            "provider",
            "observation_source",
            "authenticity_verified",
        }

    def test_non_allowlisted_keys_are_stripped(self):
        event = _event(
            {
                "attempt_id": "att_1",
                "provider": "razorpay",
                "raw_provider_payload": '{"order_id":"order_123"}',
                "conversation": "buy me a phone",
                "secret_key": "sk_test_123",
                "internal_note": "tolerance rules",
            }
        )
        redacted = _redact_event(event)
        assert set(redacted.metadata) == {"attempt_id", "provider"}
        assert "secret_key" not in redacted.metadata
        assert "sk_test_123" not in str(redacted.metadata)

    def test_all_keys_stripped_yields_empty_metadata(self):
        event = _event({"conversation": "hello", "secret_key": "sk_test_9"})
        redacted = _redact_event(event)
        assert redacted.metadata == {}
        assert redacted is not event  # new instance produced
        assert redacted.reason_code == event.reason_code  # other fields intact

    def test_allowlist_is_frozen(self):
        with pytest.raises(AttributeError):
            AUDIT_METADATA_ALLOWLIST.add("rogue_key")  # type: ignore[attr-defined]


class TestAdapterAuditRedaction:
    def test_get_transaction_audit_enforces_allowlist(self):
        """The MCP/chat shared read path must never emit non-allowlisted keys."""
        page = AuditPage(
            items=(
                _event(
                    {
                        "merchant_id": "mer_1",
                        "secret_key": "sk_test_123",
                        "raw_provider_payload": "order_987",
                    }
                ),
            ),
            next_cursor=None,
        )
        adapter = _adapter_with_page(page)

        result = adapter.get_transaction_audit(_actor(), _invocation(), _audit_request())

        assert len(result.items) == 1
        assert result.items[0].metadata == {"merchant_id": "mer_1"}
        assert "sk_test_123" not in str(result)
        assert "order_987" not in str(result)

    def test_allowlisted_keys_remain_useful_for_reconstruction(self):
        """SECURITY.md: metadata 'remains useful' — scope refs must survive."""
        page = AuditPage(
            items=(
                _event(
                    {
                        "proposal_id": "prop_1",
                        "buyer_authorization_id": "auth_1",
                        "merchant_decision_id": "dec_1",
                        "buyer_id": "buyer_1",
                        "merchant_id": "mer_1",
                        "attempt_id": "att_1",
                        "attempt_number": 2,
                        "provider": "razorpay",
                        "observation_source": "webhook",
                        "authenticity_verified": True,
                    }
                ),
            ),
            next_cursor=None,
        )
        adapter = _adapter_with_page(page)

        result = adapter.get_transaction_audit(_actor(), _invocation(), _audit_request())

        assert len(result.items[0].metadata) == 10  # all ten allowlisted keys survive
