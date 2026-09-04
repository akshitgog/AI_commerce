from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_commerce_gateway.domain.enums import (
    AuthorizationStatus,
    MerchantDecisionValue,
    PolicyMode,
    ProductStatus,
    ProposalStatus,
    TransactionState,
)
from ai_commerce_gateway.domain.proposal_gates import (
    BuyerAuthorization,
    MerchantDecision,
    MerchantPolicySnapshot,
    PurchaseProposal,
    TrustedProductSnapshot,
)
from ai_commerce_gateway.domain.transactions import Transaction
from ai_commerce_gateway.infrastructure.database import models


class SqlAlchemyProposalGateRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def buyer_is_active(self, buyer_id: str) -> bool:
        buyer = self._session.get(models.Buyer, buyer_id)
        return buyer is not None and buyer.status == "ACTIVE"

    def get_product(self, product_id: str) -> TrustedProductSnapshot | None:
        record = self._session.get(models.Product, product_id)
        if record is None:
            return None
        return TrustedProductSnapshot(
            id=record.id,
            merchant_id=record.merchant_id,
            version=record.version,
            price_minor=record.price_minor,
            currency=record.currency,
            available_quantity=record.available_quantity,
            status=ProductStatus(record.status),
        )

    def add_proposal(self, proposal: PurchaseProposal) -> None:
        self._session.add(
            models.PurchaseProposal(
                id=proposal.id,
                buyer_id=proposal.buyer_id,
                merchant_id=proposal.merchant_id,
                product_id=proposal.product_id,
                product_version=proposal.product_version,
                quantity=proposal.quantity,
                unit_price_minor=proposal.unit_price_minor,
                total_minor=proposal.total_minor,
                currency=proposal.currency,
                proposal_hash=proposal.proposal_hash,
                status=proposal.status.value,
                expires_at=proposal.expires_at,
                created_at=proposal.created_at,
            )
        )
        self._session.flush()

    def get_proposal(self, proposal_id: str) -> PurchaseProposal | None:
        record = self._session.get(models.PurchaseProposal, proposal_id)
        return self._proposal_to_domain(record) if record is not None else None

    def add_authorization(self, authorization: BuyerAuthorization) -> None:
        self._session.add(
            models.BuyerAuthorization(
                id=authorization.id,
                buyer_id=authorization.buyer_id,
                proposal_id=authorization.proposal_id,
                proposal_hash=authorization.proposal_hash,
                merchant_id=authorization.merchant_id,
                product_id=authorization.product_id,
                max_quantity=authorization.max_quantity,
                max_amount_minor=authorization.max_amount_minor,
                currency=authorization.currency,
                authorized_by=authorization.authorized_by,
                status=authorization.status.value,
                expires_at=authorization.expires_at,
                created_at=authorization.created_at,
            )
        )
        self._session.flush()

    def save_authorization(self, authorization: BuyerAuthorization) -> None:
        record = self._session.get(models.BuyerAuthorization, authorization.id)
        if record is None:
            raise LookupError(f"authorization {authorization.id} disappeared")
        record.proposal_hash = authorization.proposal_hash
        record.max_quantity = authorization.max_quantity
        record.max_amount_minor = authorization.max_amount_minor
        record.currency = authorization.currency
        record.authorized_by = authorization.authorized_by
        record.status = authorization.status.value
        record.expires_at = authorization.expires_at
        self._session.flush()

    def get_latest_authorization(self, proposal_id: str) -> BuyerAuthorization | None:
        record = self._session.scalar(
            select(models.BuyerAuthorization)
            .where(models.BuyerAuthorization.proposal_id == proposal_id)
            .order_by(
                models.BuyerAuthorization.created_at.desc(), models.BuyerAuthorization.id.desc()
            )
            .limit(1)
        )
        return self._authorization_to_domain(record) if record is not None else None

    def get_active_policy(self, merchant_id: str) -> MerchantPolicySnapshot | None:
        record = self._session.scalar(
            select(models.MerchantPolicy)
            .where(
                models.MerchantPolicy.merchant_id == merchant_id,
                models.MerchantPolicy.status == "ACTIVE",
            )
            .order_by(models.MerchantPolicy.version.desc())
            .limit(1)
        )
        if record is None:
            return None
        return MerchantPolicySnapshot(
            id=record.id,
            merchant_id=record.merchant_id,
            mode=PolicyMode(record.mode),
            auto_accept_max_minor=record.auto_accept_max_minor,
            currency=record.currency,
            version=record.version,
        )

    def add_merchant_decision(self, decision: MerchantDecision) -> None:
        self._session.add(
            models.MerchantDecision(
                id=decision.id,
                proposal_id=decision.proposal_id,
                merchant_id=decision.merchant_id,
                policy_id=decision.policy_id,
                policy_version=decision.policy_version,
                decision=decision.decision.value,
                reason_code=decision.reason_code,
                decided_by=decision.decided_by,
                expires_at=decision.expires_at,
                created_at=decision.created_at,
            )
        )
        self._session.flush()

    def get_latest_merchant_decision(self, proposal_id: str) -> MerchantDecision | None:
        record = self._session.scalar(
            select(models.MerchantDecision)
            .where(models.MerchantDecision.proposal_id == proposal_id)
            .order_by(models.MerchantDecision.created_at.desc(), models.MerchantDecision.id.desc())
            .limit(1)
        )
        return self._merchant_decision_to_domain(record) if record is not None else None

    def get_transaction_by_proposal(self, proposal_id: str) -> Transaction | None:
        record = self._session.scalar(
            select(models.Transaction).where(models.Transaction.proposal_id == proposal_id)
        )
        return self._transaction_to_domain(record) if record is not None else None

    def add_ready_transaction(
        self,
        transaction: Transaction,
        *,
        event_id: str,
        actor_type: str,
        actor_id: str | None,
        correlation_id: str,
    ) -> None:
        self._session.add(
            models.Transaction(
                id=transaction.id,
                proposal_id=transaction.proposal_id,
                buyer_authorization_id=transaction.buyer_authorization_id,
                merchant_decision_id=transaction.merchant_decision_id,
                merchant_id=transaction.merchant_id,
                buyer_id=transaction.buyer_id,
                amount_minor=transaction.amount_minor,
                currency=transaction.currency,
                state=transaction.state.value,
                created_at=transaction.created_at,
                updated_at=transaction.updated_at,
            )
        )
        self._session.add(
            models.TransactionEvent(
                id=event_id,
                transaction_id=transaction.id,
                event_type="TRANSACTION_CREATED",
                actor_type=actor_type,
                actor_id=actor_id,
                reason_code="GATES_SATISFIED",
                previous_state=None,
                new_state=TransactionState.READY.value,
                correlation_id=correlation_id,
                provider_reference_redacted=None,
                metadata_json={
                    "proposal_id": transaction.proposal_id,
                    "buyer_authorization_id": transaction.buyer_authorization_id,
                    "merchant_decision_id": transaction.merchant_decision_id,
                    "merchant_id": transaction.merchant_id,
                    "buyer_id": transaction.buyer_id,
                    "amount_minor": transaction.amount_minor,
                    "currency": transaction.currency,
                },
                created_at=transaction.created_at,
            )
        )
        self._session.flush()

    @staticmethod
    def _proposal_to_domain(record: models.PurchaseProposal) -> PurchaseProposal:
        return PurchaseProposal(
            id=record.id,
            buyer_id=record.buyer_id,
            merchant_id=record.merchant_id,
            product_id=record.product_id,
            product_version=record.product_version,
            quantity=record.quantity,
            unit_price_minor=record.unit_price_minor,
            total_minor=record.total_minor,
            currency=record.currency,
            proposal_hash=record.proposal_hash,
            status=ProposalStatus(record.status),
            expires_at=_as_utc(record.expires_at),
            created_at=_as_utc(record.created_at),
        )

    @staticmethod
    def _authorization_to_domain(record: models.BuyerAuthorization) -> BuyerAuthorization:
        return BuyerAuthorization(
            id=record.id,
            buyer_id=record.buyer_id,
            proposal_id=record.proposal_id,
            proposal_hash=record.proposal_hash,
            merchant_id=record.merchant_id,
            product_id=record.product_id,
            max_quantity=record.max_quantity,
            max_amount_minor=record.max_amount_minor,
            currency=record.currency,
            authorized_by=record.authorized_by,
            status=AuthorizationStatus(record.status),
            expires_at=_as_utc(record.expires_at),
            created_at=_as_utc(record.created_at),
        )

    @staticmethod
    def _merchant_decision_to_domain(record: models.MerchantDecision) -> MerchantDecision:
        return MerchantDecision(
            id=record.id,
            proposal_id=record.proposal_id,
            merchant_id=record.merchant_id,
            policy_id=record.policy_id,
            policy_version=record.policy_version,
            decision=MerchantDecisionValue(record.decision),
            reason_code=record.reason_code,
            decided_by=record.decided_by,
            expires_at=_as_utc(record.expires_at) if record.expires_at is not None else None,
            created_at=_as_utc(record.created_at),
        )

    @staticmethod
    def _transaction_to_domain(record: models.Transaction) -> Transaction:
        return Transaction(
            id=record.id,
            proposal_id=record.proposal_id,
            buyer_authorization_id=record.buyer_authorization_id,
            merchant_decision_id=record.merchant_decision_id,
            merchant_id=record.merchant_id,
            buyer_id=record.buyer_id,
            amount_minor=record.amount_minor,
            currency=record.currency,
            state=TransactionState(record.state),
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
        )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
