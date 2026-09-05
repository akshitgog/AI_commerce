"""Regression tests for the transaction facade's persistence boundary."""

from datetime import UTC, datetime
from typing import Any, cast

from ai_commerce_gateway.application.transaction_service import (
    TransactionApplicationService,
)
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    CreateTransactionCommand,
    Money,
    TransactionView,
)
from ai_commerce_gateway.domain.enums import ActorType, TransactionState


class RecordingCreationService:
    def __init__(self, transaction: TransactionView, calls: list[str]) -> None:
        self._transaction = transaction
        self._calls = calls

    def create(self, command: CreateTransactionCommand, actor: ActorContext) -> TransactionView:
        assert command.proposal_id == self._transaction.proposal_id
        assert actor.actor_id == self._transaction.buyer_id
        self._calls.append("create")
        return self._transaction


def test_create_commits_ready_transaction_before_separate_execution_uow() -> None:
    now = datetime.now(UTC)
    transaction = TransactionView(
        id="txn_123",
        proposal_id="prop_123",
        merchant_id="mer_123",
        buyer_id="buyer_123",
        amount=Money(amount_minor=100_000, currency="INR"),
        state=TransactionState.READY,
        created_at=now,
        updated_at=now,
    )
    calls: list[str] = []
    service = TransactionApplicationService(
        creation=RecordingCreationService(transaction, calls),
        execution=cast(Any, object()),
        reconciliation=cast(Any, object()),
        queries=cast(Any, object()),
        commit_created_transaction=lambda: calls.append("commit"),
    )

    result = service.create(
        CreateTransactionCommand(
            proposal_id="prop_123",
            idempotency_key="create-txn-123",
        ),
        ActorContext(
            actor_type=ActorType.BUYER,
            actor_id="buyer_123",
            correlation_id="corr_123",
        ),
    )

    assert result == transaction
    assert calls == ["create", "commit"]
