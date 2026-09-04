import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from ai_commerce_gateway.application.proposal_gates import (
    AuthorizationApplicationService,
    HumanBuyerApprovalVerifier,
    MerchantGateApplicationService,
    ProposalApplicationService,
    TransactionCreationApplicationService,
)
from ai_commerce_gateway.contracts.models import (
    ActorContext,
    ApproveAuthorizationCommand,
    CreateProposalCommand,
    CreateTransactionCommand,
    EvaluateMerchantPolicyCommand,
    Money,
    RecordMerchantDecisionCommand,
    RequestAuthorizationCommand,
)
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.core.ids import EntityPrefix
from ai_commerce_gateway.domain.enums import (
    ActorType,
    AuthorizationStatus,
    MerchantDecisionValue,
    MerchantRole,
    NextRequiredGate,
    PolicyMode,
    ProductStatus,
    TransactionState,
)
from ai_commerce_gateway.infrastructure.database import models
from ai_commerce_gateway.infrastructure.database.proposal_gates import (
    SqlAlchemyProposalGateRepository,
)

NOW = datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


class SequentialIds:
    def __init__(self) -> None:
        self._next = 0

    def __call__(self, prefix: EntityPrefix) -> str:
        self._next += 1
        return f"{prefix}_test_{self._next}"


class AllowHumanApproval(HumanBuyerApprovalVerifier):
    def verify(self, *, actor: ActorContext, buyer_id: str) -> str:
        if actor.actor_type is not ActorType.BUYER or actor.actor_id != buyer_id:
            raise AppError(ErrorCode.FORBIDDEN, "Human buyer verification failed.", status_code=403)
        return f"human-session:{buyer_id}"


class RejectAiApproval(HumanBuyerApprovalVerifier):
    def verify(self, *, actor: ActorContext, buyer_id: str) -> str:
        raise AppError(
            ErrorCode.FORBIDDEN,
            "AI identities cannot approve buyer authorization.",
            status_code=403,
        )


@contextmanager
def database_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


def seed_catalog(
    session: Session,
    *,
    policy_mode: PolicyMode = PolicyMode.AUTO_BELOW_LIMIT,
    policy_limit: int | None = 200_000,
) -> None:
    session.add_all(
        [
            models.Merchant(id="mer_test", name="Merchant", status="ACTIVE"),
            models.Merchant(id="mer_other", name="Other", status="ACTIVE"),
            models.Buyer(id="buy_test", external_identity="buyer@test", status="ACTIVE"),
            models.Buyer(id="buy_other", external_identity="other@test", status="ACTIVE"),
            models.Product(
                id="prod_test",
                merchant_id="mer_test",
                sku="sku-test",
                title="Trusted Product",
                description="Database-backed fixture",
                category=None,
                price_minor=50_000,
                currency="INR",
                available_quantity=5,
                status=ProductStatus.PUBLISHED.value,
                version=3,
            ),
            models.MerchantPolicy(
                id="pol_test",
                merchant_id="mer_test",
                mode=policy_mode.value,
                auto_accept_max_minor=policy_limit,
                currency="INR" if policy_limit is not None else None,
                version=1,
                status="ACTIVE",
            ),
        ]
    )
    session.flush()


def buyer_actor(buyer_id: str = "buy_test") -> ActorContext:
    return ActorContext(
        actor_id=buyer_id,
        actor_type=ActorType.BUYER,
        correlation_id="corr_test",
    )


def merchant_actor(merchant_id: str = "mer_test") -> ActorContext:
    return ActorContext(
        actor_id="merchant_user_test",
        actor_type=ActorType.MERCHANT_USER,
        merchant_ids=frozenset({merchant_id}),
        roles=frozenset({MerchantRole.APPROVER}),
        correlation_id="corr_test",
    )


def create_and_request(
    repository: SqlAlchemyProposalGateRepository,
    ids: SequentialIds,
) -> tuple[ProposalApplicationService, AuthorizationApplicationService, str, str]:
    proposals = ProposalApplicationService(repository, clock=lambda: NOW, id_factory=ids)
    authorization = AuthorizationApplicationService(
        repository,
        AllowHumanApproval(),
        clock=lambda: NOW,
        id_factory=ids,
    )
    proposal_view = proposals.create(
        CreateProposalCommand(
            merchant_id="mer_test",
            product_id="prod_test",
            quantity=2,
            idempotency_key="proposal-1",
        ),
        buyer_actor(),
    )
    authorization_view = authorization.request(
        RequestAuthorizationCommand(
            proposal_id=proposal_view.id,
            idempotency_key="authorization-request-1",
        ),
        buyer_actor(),
    )
    return proposals, authorization, proposal_view.id, authorization_view.id


def approve_exact_proposal(
    proposals: ProposalApplicationService,
    authorization: AuthorizationApplicationService,
    proposal_id: str,
) -> None:
    proposal_view = proposals.get(proposal_id, buyer_actor())
    authorization.approve(
        ApproveAuthorizationCommand(
            proposal_id=proposal_id,
            proposal_hash=proposal_view.proposal_hash,
            max_quantity=proposal_view.quantity,
            max_amount=proposal_view.total,
            expires_at=proposal_view.expires_at,
            idempotency_key="authorization-approve-1",
        ),
        buyer_actor(),
    )


def test_complete_auto_allow_flow_creates_ready_transaction_and_audit_event() -> None:
    with database_session() as session:
        seed_catalog(session)
        repository = SqlAlchemyProposalGateRepository(session)
        ids = SequentialIds()
        proposals, authorization, proposal_id, authorization_id = create_and_request(
            repository, ids
        )

        persisted_proposal = session.get(models.PurchaseProposal, proposal_id)
        assert persisted_proposal is not None
        assert persisted_proposal.unit_price_minor == 50_000
        assert persisted_proposal.total_minor == 100_000
        assert persisted_proposal.product_version == 3

        merchant_gate = MerchantGateApplicationService(
            repository, clock=lambda: NOW, id_factory=ids
        )
        with pytest.raises(AppError) as missing_authorization:
            merchant_gate.evaluate(
                EvaluateMerchantPolicyCommand(proposal_id=proposal_id), buyer_actor()
            )
        assert missing_authorization.value.code is ErrorCode.AUTHORIZATION_INVALID

        approve_exact_proposal(proposals, authorization, proposal_id)
        decision = merchant_gate.evaluate(
            EvaluateMerchantPolicyCommand(proposal_id=proposal_id), buyer_actor()
        )
        assert decision.decision is MerchantDecisionValue.ALLOW
        assert (
            proposals.get(proposal_id, buyer_actor()).next_required_gate is NextRequiredGate.READY
        )

        transaction_service = TransactionCreationApplicationService(
            repository, clock=lambda: NOW, id_factory=ids
        )
        transaction = transaction_service.create(
            CreateTransactionCommand(proposal_id=proposal_id, idempotency_key="transaction-1"),
            buyer_actor(),
        )
        repeated = transaction_service.create(
            CreateTransactionCommand(proposal_id=proposal_id, idempotency_key="transaction-2"),
            buyer_actor(),
        )

        assert transaction.state is TransactionState.READY
        assert transaction.amount == Money(amount_minor=100_000, currency="INR")
        assert repeated.id == transaction.id
        persisted_transaction = session.get(models.Transaction, transaction.id)
        assert persisted_transaction is not None
        assert persisted_transaction.buyer_authorization_id == authorization_id
        assert persisted_transaction.merchant_decision_id == decision.id
        event = session.scalar(
            select(models.TransactionEvent).where(
                models.TransactionEvent.transaction_id == transaction.id
            )
        )
        assert event is not None
        assert event.previous_state is None
        assert event.new_state == TransactionState.READY.value
        assert event.reason_code == "GATES_SATISFIED"
        assert session.scalar(select(func.count()).select_from(models.PaymentAttempt)) == 0


def test_ai_identity_cannot_approve_its_requested_authorization() -> None:
    with database_session() as session:
        seed_catalog(session)
        repository = SqlAlchemyProposalGateRepository(session)
        ids = SequentialIds()
        proposals, _, proposal_id, authorization_id = create_and_request(repository, ids)
        ai_facing_service = AuthorizationApplicationService(
            repository,
            RejectAiApproval(),
            clock=lambda: NOW,
            id_factory=ids,
        )
        proposal_view = proposals.get(proposal_id, buyer_actor())

        with pytest.raises(AppError) as error:
            ai_facing_service.approve(
                ApproveAuthorizationCommand(
                    proposal_id=proposal_id,
                    proposal_hash=proposal_view.proposal_hash,
                    max_quantity=proposal_view.quantity,
                    max_amount=proposal_view.total,
                    expires_at=proposal_view.expires_at,
                    idempotency_key="ai-must-not-approve",
                ),
                buyer_actor(),
            )
        assert error.value.code is ErrorCode.FORBIDDEN
        record = session.get(models.BuyerAuthorization, authorization_id)
        assert record is not None
        assert record.status == AuthorizationStatus.REQUESTED.value
        assert record.authorized_by is None


def test_manual_review_requires_the_correct_merchant_approver() -> None:
    with database_session() as session:
        seed_catalog(session, policy_mode=PolicyMode.MANUAL_ALL, policy_limit=None)
        repository = SqlAlchemyProposalGateRepository(session)
        ids = SequentialIds()
        proposals, authorization, proposal_id, _ = create_and_request(repository, ids)
        approve_exact_proposal(proposals, authorization, proposal_id)
        merchant_gate = MerchantGateApplicationService(
            repository, clock=lambda: NOW, id_factory=ids
        )
        review = merchant_gate.evaluate(
            EvaluateMerchantPolicyCommand(proposal_id=proposal_id), buyer_actor()
        )
        assert review.decision is MerchantDecisionValue.REVIEW_REQUIRED
        assert (
            proposals.get(proposal_id, buyer_actor()).next_required_gate
            is NextRequiredGate.MERCHANT_REVIEW_REQUIRED
        )

        command = RecordMerchantDecisionCommand(
            proposal_id=proposal_id,
            decision=MerchantDecisionValue.ALLOW,
            reason_code="MERCHANT_APPROVED",
            idempotency_key="manual-1",
        )
        with pytest.raises(AppError) as wrong_tenant:
            merchant_gate.record_manual_decision(command, merchant_actor("mer_other"))
        assert wrong_tenant.value.code is ErrorCode.FORBIDDEN

        allowed = merchant_gate.record_manual_decision(command, merchant_actor())
        assert allowed.decision is MerchantDecisionValue.ALLOW
        assert allowed.decided_by == "merchant_user_test"
        assert (
            proposals.get(proposal_id, buyer_actor()).next_required_gate is NextRequiredGate.READY
        )


def test_product_version_drift_blocks_ready_transaction_creation() -> None:
    with database_session() as session:
        seed_catalog(session)
        repository = SqlAlchemyProposalGateRepository(session)
        ids = SequentialIds()
        proposals, authorization, proposal_id, _ = create_and_request(repository, ids)
        approve_exact_proposal(proposals, authorization, proposal_id)
        MerchantGateApplicationService(repository, clock=lambda: NOW, id_factory=ids).evaluate(
            EvaluateMerchantPolicyCommand(proposal_id=proposal_id), buyer_actor()
        )
        product = session.get(models.Product, "prod_test")
        assert product is not None
        product.version += 1
        session.flush()

        with pytest.raises(AppError) as error:
            TransactionCreationApplicationService(
                repository, clock=lambda: NOW, id_factory=ids
            ).create(
                CreateTransactionCommand(
                    proposal_id=proposal_id,
                    idempotency_key="transaction-stale",
                ),
                buyer_actor(),
            )
        assert error.value.code is ErrorCode.PROPOSAL_STALE
        assert session.scalar(select(func.count()).select_from(models.Transaction)) == 0


def test_transaction_creation_requires_buyer_and_merchant_gates_separately() -> None:
    with database_session() as session:
        seed_catalog(session)
        repository = SqlAlchemyProposalGateRepository(session)
        ids = SequentialIds()
        proposals = ProposalApplicationService(repository, clock=lambda: NOW, id_factory=ids)
        proposal = proposals.create(
            CreateProposalCommand(
                merchant_id="mer_test",
                product_id="prod_test",
                quantity=1,
                idempotency_key="proposal-1",
            ),
            buyer_actor(),
        )
        transactions = TransactionCreationApplicationService(
            repository, clock=lambda: NOW, id_factory=ids
        )
        command = CreateTransactionCommand(proposal_id=proposal.id, idempotency_key="transaction-1")

        with pytest.raises(AppError) as buyer_gate:
            transactions.create(command, buyer_actor())
        assert buyer_gate.value.code is ErrorCode.AUTHORIZATION_REQUIRED

        authorization = AuthorizationApplicationService(
            repository,
            AllowHumanApproval(),
            clock=lambda: NOW,
            id_factory=ids,
        )
        authorization.request(
            RequestAuthorizationCommand(
                proposal_id=proposal.id,
                idempotency_key="authorization-request-1",
            ),
            buyer_actor(),
        )
        approve_exact_proposal(proposals, authorization, proposal.id)
        with pytest.raises(AppError) as merchant_gate:
            transactions.create(command, buyer_actor())
        assert merchant_gate.value.code is ErrorCode.MERCHANT_REVIEW_REQUIRED


def test_policy_version_change_invalidates_an_earlier_allow_decision() -> None:
    with database_session() as session:
        seed_catalog(session)
        repository = SqlAlchemyProposalGateRepository(session)
        ids = SequentialIds()
        proposals, authorization, proposal_id, _ = create_and_request(repository, ids)
        approve_exact_proposal(proposals, authorization, proposal_id)
        MerchantGateApplicationService(repository, clock=lambda: NOW, id_factory=ids).evaluate(
            EvaluateMerchantPolicyCommand(proposal_id=proposal_id), buyer_actor()
        )
        session.add(
            models.MerchantPolicy(
                id="pol_test_v2",
                merchant_id="mer_test",
                mode=PolicyMode.MANUAL_ALL.value,
                auto_accept_max_minor=None,
                currency=None,
                version=2,
                status="ACTIVE",
            )
        )
        session.flush()

        assert (
            proposals.get(proposal_id, buyer_actor()).next_required_gate
            is NextRequiredGate.MERCHANT_POLICY_PENDING
        )
        with pytest.raises(AppError) as error:
            TransactionCreationApplicationService(
                repository, clock=lambda: NOW, id_factory=ids
            ).create(
                CreateTransactionCommand(
                    proposal_id=proposal_id,
                    idempotency_key="transaction-policy-changed",
                ),
                buyer_actor(),
            )
        assert error.value.code is ErrorCode.MERCHANT_REVIEW_REQUIRED


def test_cross_buyer_and_cross_merchant_proposal_access_is_denied() -> None:
    with database_session() as session:
        seed_catalog(session)
        repository = SqlAlchemyProposalGateRepository(session)
        ids = SequentialIds()
        proposals, _, proposal_id, _ = create_and_request(repository, ids)

        with pytest.raises(AppError) as wrong_buyer:
            proposals.get(proposal_id, buyer_actor("buy_other"))
        assert wrong_buyer.value.code is ErrorCode.FORBIDDEN
        with pytest.raises(AppError) as wrong_merchant:
            proposals.get(proposal_id, merchant_actor("mer_other"))
        assert wrong_merchant.value.code is ErrorCode.FORBIDDEN


@pytest.mark.integration
def test_proposal_gate_flow_in_postgresql_when_configured() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")
    engine = create_engine(database_url, pool_pre_ping=True)
    connection = engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)
    try:
        seed_catalog(session)
        repository = SqlAlchemyProposalGateRepository(session)
        ids = SequentialIds()
        proposals, authorization, proposal_id, _ = create_and_request(repository, ids)
        approve_exact_proposal(proposals, authorization, proposal_id)
        MerchantGateApplicationService(repository, clock=lambda: NOW, id_factory=ids).evaluate(
            EvaluateMerchantPolicyCommand(proposal_id=proposal_id), buyer_actor()
        )
        transaction = TransactionCreationApplicationService(
            repository, clock=lambda: NOW, id_factory=ids
        ).create(
            CreateTransactionCommand(
                proposal_id=proposal_id,
                idempotency_key="postgres-transaction",
            ),
            buyer_actor(),
        )
        assert transaction.state is TransactionState.READY
        assert session.scalar(select(func.count()).select_from(models.TransactionEvent)) == 1
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()
        engine.dispose()
