from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast

from ai_commerce_gateway.contracts.models import (
    ActorContext,
    ApproveAuthorizationCommand,
    BuyerAuthorizationView,
    CreateProposalCommand,
    CreateTransactionCommand,
    EvaluateMerchantPolicyCommand,
    MerchantDecisionView,
    Money,
    PurchaseProposalView,
    RecordMerchantDecisionCommand,
    RequestAuthorizationCommand,
    TransactionView,
)
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.core.ids import EntityPrefix, new_id
from ai_commerce_gateway.domain.enums import (
    ActorType,
    AuthorizationStatus,
    MerchantRole,
    NextRequiredGate,
    TransactionState,
)
from ai_commerce_gateway.domain.proposal_gates import (
    BuyerAuthorization,
    MerchantDecision,
    MerchantPolicySnapshot,
    PurchaseProposal,
    TrustedProductSnapshot,
    create_purchase_proposal,
    determine_next_gate,
    evaluate_merchant_policy,
    record_manual_merchant_decision,
    request_buyer_authorization,
    require_current_product,
)
from ai_commerce_gateway.domain.transactions import Transaction

Clock = Callable[[], datetime]
IdFactory = Callable[[EntityPrefix], str]
DEFAULT_PROPOSAL_TTL = timedelta(minutes=15)


class HumanBuyerApprovalVerifier(Protocol):
    """Trusted adapter boundary that proves approval came from a human-controlled surface."""

    def verify(self, *, actor: ActorContext, buyer_id: str) -> str: ...


class ProposalGateRepository(Protocol):
    def buyer_is_active(self, buyer_id: str) -> bool: ...
    def get_product(self, product_id: str) -> TrustedProductSnapshot | None: ...
    def add_proposal(self, proposal: PurchaseProposal) -> None: ...
    def get_proposal(self, proposal_id: str) -> PurchaseProposal | None: ...
    def add_authorization(self, authorization: BuyerAuthorization) -> None: ...
    def save_authorization(self, authorization: BuyerAuthorization) -> None: ...
    def get_latest_authorization(self, proposal_id: str) -> BuyerAuthorization | None: ...
    def get_active_policy(self, merchant_id: str) -> MerchantPolicySnapshot | None: ...
    def add_merchant_decision(self, decision: MerchantDecision) -> None: ...
    def get_latest_merchant_decision(self, proposal_id: str) -> MerchantDecision | None: ...
    def get_transaction_by_proposal(self, proposal_id: str) -> Transaction | None: ...
    def add_ready_transaction(
        self,
        transaction: Transaction,
        *,
        event_id: str,
        actor_type: str,
        actor_id: str | None,
        correlation_id: str,
    ) -> None: ...


class ProposalApplicationService:
    def __init__(
        self,
        repository: ProposalGateRepository,
        *,
        clock: Clock | None = None,
        id_factory: IdFactory = new_id,
        proposal_ttl: timedelta = DEFAULT_PROPOSAL_TTL,
    ) -> None:
        if proposal_ttl <= timedelta(0):
            raise ValueError("proposal_ttl must be positive")
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory
        self._proposal_ttl = proposal_ttl

    def create(self, command: CreateProposalCommand, actor: ActorContext) -> PurchaseProposalView:
        _require_buyer_actor(actor)
        if not self._repository.buyer_is_active(actor.actor_id):
            raise AppError(ErrorCode.FORBIDDEN, "Buyer is not active.", status_code=403)
        product = self._repository.get_product(command.product_id)
        if product is None:
            raise AppError(ErrorCode.NOT_FOUND, "Product was not found.", status_code=404)
        now = self._clock()
        proposal = create_purchase_proposal(
            proposal_id=self._id_factory("prop"),
            buyer_id=actor.actor_id,
            requested_merchant_id=command.merchant_id,
            product=product,
            quantity=command.quantity,
            created_at=now,
            expires_at=now + self._proposal_ttl,
        )
        self._repository.add_proposal(proposal)
        return _proposal_view(proposal, NextRequiredGate.BUYER_AUTH_REQUIRED)

    def get(self, proposal_id: str, actor: ActorContext) -> PurchaseProposalView:
        proposal = _get_proposal(self._repository, proposal_id)
        _require_proposal_access(actor, proposal)
        now = self._clock()
        authorization = self._repository.get_latest_authorization(proposal.id)
        decision = _get_current_merchant_decision(self._repository, proposal)
        gate = determine_next_gate(proposal, authorization, decision, now=now)
        return _proposal_view(proposal, gate)


class AuthorizationApplicationService:
    def __init__(
        self,
        repository: ProposalGateRepository,
        approval_verifier: HumanBuyerApprovalVerifier,
        *,
        clock: Clock | None = None,
        id_factory: IdFactory = new_id,
    ) -> None:
        self._repository = repository
        self._approval_verifier = approval_verifier
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory

    def request(
        self, command: RequestAuthorizationCommand, actor: ActorContext
    ) -> BuyerAuthorizationView:
        proposal = _get_proposal(self._repository, command.proposal_id)
        _require_buyer_actor(actor, expected_buyer_id=proposal.buyer_id)
        now = self._clock()
        proposal.require_active(now)
        existing = self._repository.get_latest_authorization(proposal.id)
        if (
            existing is not None
            and existing.status
            in {
                AuthorizationStatus.REQUESTED,
                AuthorizationStatus.APPROVED,
            }
            and now < existing.expires_at
        ):
            return _authorization_view(existing, now)
        authorization = request_buyer_authorization(
            authorization_id=self._id_factory("auth"),
            proposal=proposal,
            requested_at=now,
        )
        self._repository.add_authorization(authorization)
        return _authorization_view(authorization, now)

    def approve(
        self, command: ApproveAuthorizationCommand, actor: ActorContext
    ) -> BuyerAuthorizationView:
        proposal = _get_proposal(self._repository, command.proposal_id)
        _require_buyer_actor(actor, expected_buyer_id=proposal.buyer_id)
        authorized_by = self._approval_verifier.verify(actor=actor, buyer_id=proposal.buyer_id)
        authorization = self._repository.get_latest_authorization(proposal.id)
        if authorization is None:
            raise AppError(
                ErrorCode.AUTHORIZATION_REQUIRED,
                "Buyer authorization must be requested before approval.",
                status_code=409,
            )
        now = self._clock()
        approved = authorization.approve(
            proposal,
            proposal_hash=command.proposal_hash,
            max_quantity=command.max_quantity,
            max_amount_minor=command.max_amount.amount_minor,
            currency=command.max_amount.currency,
            expires_at=command.expires_at,
            authorized_by=authorized_by,
            now=now,
        )
        self._repository.save_authorization(approved)
        return _authorization_view(approved, now)


class MerchantGateApplicationService:
    def __init__(
        self,
        repository: ProposalGateRepository,
        *,
        clock: Clock | None = None,
        id_factory: IdFactory = new_id,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory

    def evaluate(
        self, command: EvaluateMerchantPolicyCommand, actor: ActorContext
    ) -> MerchantDecisionView:
        proposal = _get_proposal(self._repository, command.proposal_id)
        _require_proposal_access(actor, proposal)
        now = self._clock()
        authorization = self._repository.get_latest_authorization(proposal.id)
        if authorization is None:
            raise AppError(
                ErrorCode.AUTHORIZATION_REQUIRED,
                "Buyer authorization is required before merchant evaluation.",
                status_code=409,
            )
        authorization.require_matches(proposal, now=now)
        policy = self._repository.get_active_policy(proposal.merchant_id)
        if policy is None:
            raise AppError(
                ErrorCode.NOT_FOUND, "Active merchant policy was not found.", status_code=404
            )
        decision = evaluate_merchant_policy(
            decision_id=self._id_factory("mdec"),
            proposal=proposal,
            policy=policy,
            decided_at=now,
        )
        self._repository.add_merchant_decision(decision)
        return _merchant_decision_view(decision)

    def record_manual_decision(
        self, command: RecordMerchantDecisionCommand, actor: ActorContext
    ) -> MerchantDecisionView:
        proposal = _get_proposal(self._repository, command.proposal_id)
        _require_merchant_approver(actor, proposal.merchant_id)
        review_decision = self._repository.get_latest_merchant_decision(proposal.id)
        if review_decision is None:
            raise AppError(
                ErrorCode.MERCHANT_REVIEW_REQUIRED,
                "Merchant policy must request review before a manual decision.",
                status_code=409,
            )
        policy = self._repository.get_active_policy(proposal.merchant_id)
        if policy is None or not review_decision.is_current_for(policy):
            raise AppError(
                ErrorCode.INVALID_STATE,
                "Merchant policy changed; evaluate the proposal again.",
                status_code=409,
            )
        now = self._clock()
        decided_at = max(now, review_decision.created_at + timedelta(microseconds=1))
        decision = record_manual_merchant_decision(
            decision_id=self._id_factory("mdec"),
            proposal=proposal,
            review_decision=review_decision,
            decision=command.decision,
            reason_code=command.reason_code,
            decided_by=actor.actor_id,
            expires_at=command.expires_at,
            decided_at=decided_at,
        )
        self._repository.add_merchant_decision(decision)
        return _merchant_decision_view(decision)


class TransactionCreationApplicationService:
    """B2 transaction.create slice; execution and reconciliation remain later phases."""

    def __init__(
        self,
        repository: ProposalGateRepository,
        *,
        clock: Clock | None = None,
        id_factory: IdFactory = new_id,
    ) -> None:
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory

    def create(self, command: CreateTransactionCommand, actor: ActorContext) -> TransactionView:
        proposal = _get_proposal(self._repository, command.proposal_id)
        _require_buyer_actor(actor, expected_buyer_id=proposal.buyer_id)
        existing = self._repository.get_transaction_by_proposal(proposal.id)
        if existing is not None:
            return _transaction_view(existing)

        now = self._clock()
        authorization = self._repository.get_latest_authorization(proposal.id)
        decision = _get_current_merchant_decision(self._repository, proposal)
        gate = determine_next_gate(proposal, authorization, decision, now=now)
        if gate is NextRequiredGate.BUYER_AUTH_REQUIRED:
            raise AppError(
                ErrorCode.AUTHORIZATION_REQUIRED,
                "An active buyer authorization is required.",
                status_code=409,
            )
        if gate is not NextRequiredGate.READY:
            raise AppError(
                ErrorCode.MERCHANT_REVIEW_REQUIRED,
                "An active merchant acceptance is required.",
                status_code=409,
            )
        authorization = cast(BuyerAuthorization, authorization)
        decision = cast(MerchantDecision, decision)
        product = self._repository.get_product(proposal.product_id)
        if product is None:
            raise AppError(
                ErrorCode.PROPOSAL_STALE, "Proposal product no longer exists.", status_code=409
            )
        require_current_product(proposal, product)

        transaction = Transaction(
            id=self._id_factory("txn"),
            proposal_id=proposal.id,
            buyer_authorization_id=authorization.id,
            merchant_decision_id=decision.id,
            merchant_id=proposal.merchant_id,
            buyer_id=proposal.buyer_id,
            amount_minor=proposal.total_minor,
            currency=proposal.currency,
            state=TransactionState.READY,
            created_at=now,
            updated_at=now,
        )
        self._repository.add_ready_transaction(
            transaction,
            event_id=self._id_factory("tevt"),
            actor_type=actor.actor_type.value,
            actor_id=actor.actor_id,
            correlation_id=actor.correlation_id,
        )
        return _transaction_view(transaction)


def _get_proposal(repository: ProposalGateRepository, proposal_id: str) -> PurchaseProposal:
    proposal = repository.get_proposal(proposal_id)
    if proposal is None:
        raise AppError(ErrorCode.NOT_FOUND, "Purchase proposal was not found.", status_code=404)
    return proposal


def _get_current_merchant_decision(
    repository: ProposalGateRepository, proposal: PurchaseProposal
) -> MerchantDecision | None:
    decision = repository.get_latest_merchant_decision(proposal.id)
    if decision is None:
        return None
    policy = repository.get_active_policy(proposal.merchant_id)
    if policy is None or not decision.is_current_for(policy):
        return None
    return decision


def _require_buyer_actor(actor: ActorContext, expected_buyer_id: str | None = None) -> None:
    if actor.actor_type is not ActorType.BUYER:
        raise AppError(ErrorCode.FORBIDDEN, "A buyer identity is required.", status_code=403)
    if expected_buyer_id is not None and actor.actor_id != expected_buyer_id:
        raise AppError(ErrorCode.FORBIDDEN, "Buyer does not own this proposal.", status_code=403)


def _require_proposal_access(actor: ActorContext, proposal: PurchaseProposal) -> None:
    buyer_access = actor.actor_type is ActorType.BUYER and actor.actor_id == proposal.buyer_id
    merchant_access = (
        actor.actor_type is ActorType.MERCHANT_USER and proposal.merchant_id in actor.merchant_ids
    )
    system_access = actor.actor_type in {ActorType.PLATFORM, ActorType.SYSTEM}
    if not (buyer_access or merchant_access or system_access):
        raise AppError(ErrorCode.FORBIDDEN, "Proposal access is forbidden.", status_code=403)


def _require_merchant_approver(actor: ActorContext, merchant_id: str) -> None:
    if (
        actor.actor_type is not ActorType.MERCHANT_USER
        or merchant_id not in actor.merchant_ids
        or not actor.roles.intersection({MerchantRole.ADMIN, MerchantRole.APPROVER})
    ):
        raise AppError(ErrorCode.FORBIDDEN, "Merchant approver role is required.", status_code=403)


def _proposal_view(
    proposal: PurchaseProposal, next_required_gate: NextRequiredGate
) -> PurchaseProposalView:
    status = proposal.status
    return PurchaseProposalView(
        id=proposal.id,
        buyer_id=proposal.buyer_id,
        merchant_id=proposal.merchant_id,
        product_id=proposal.product_id,
        product_version=proposal.product_version,
        quantity=proposal.quantity,
        unit_price=Money(amount_minor=proposal.unit_price_minor, currency=proposal.currency),
        total=Money(amount_minor=proposal.total_minor, currency=proposal.currency),
        proposal_hash=proposal.proposal_hash,
        status=status,
        next_required_gate=next_required_gate,
        expires_at=proposal.expires_at,
        created_at=proposal.created_at,
    )


def _authorization_view(authorization: BuyerAuthorization, now: datetime) -> BuyerAuthorizationView:
    status = authorization.status
    if now >= authorization.expires_at and status in {
        AuthorizationStatus.REQUESTED,
        AuthorizationStatus.APPROVED,
    }:
        status = AuthorizationStatus.EXPIRED
    return BuyerAuthorizationView(
        id=authorization.id,
        buyer_id=authorization.buyer_id,
        proposal_id=authorization.proposal_id,
        proposal_hash=authorization.proposal_hash,
        merchant_id=authorization.merchant_id,
        product_id=authorization.product_id,
        max_quantity=authorization.max_quantity,
        max_amount=Money(
            amount_minor=authorization.max_amount_minor,
            currency=authorization.currency,
        ),
        authorized_by=authorization.authorized_by,
        status=status,
        expires_at=authorization.expires_at,
        created_at=authorization.created_at,
    )


def _merchant_decision_view(decision: MerchantDecision) -> MerchantDecisionView:
    return MerchantDecisionView(
        id=decision.id,
        proposal_id=decision.proposal_id,
        merchant_id=decision.merchant_id,
        policy_id=decision.policy_id,
        policy_version=decision.policy_version,
        decision=decision.decision,
        reason_code=decision.reason_code,
        decided_by=decision.decided_by,
        expires_at=decision.expires_at,
        created_at=decision.created_at,
    )


def _transaction_view(transaction: Transaction) -> TransactionView:
    return TransactionView(
        id=transaction.id,
        proposal_id=transaction.proposal_id,
        merchant_id=transaction.merchant_id,
        buyer_id=transaction.buyer_id,
        amount=Money(amount_minor=transaction.amount_minor, currency=transaction.currency),
        state=transaction.state,
        provider_phase=None,
        created_at=transaction.created_at,
        updated_at=transaction.updated_at,
    )
