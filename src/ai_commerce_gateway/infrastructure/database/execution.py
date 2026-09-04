from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.application.transaction_execution import ExecutionRepository
from ai_commerce_gateway.contracts.models import ProviderObservation
from ai_commerce_gateway.core.ids import new_id
from ai_commerce_gateway.domain.enums import ActorType, ProviderName, TransactionState
from ai_commerce_gateway.domain.execution import IdempotencyRecord, PaymentAttempt
from ai_commerce_gateway.domain.proposal_gates import BuyerAuthorization, MerchantDecision
from ai_commerce_gateway.domain.transactions import Transaction
from ai_commerce_gateway.infrastructure.database import models
from ai_commerce_gateway.infrastructure.database.proposal_gates import (
    SqlAlchemyProposalGateRepository,
)
from ai_commerce_gateway.infrastructure.database.transactions import (
    SqlAlchemyTransactionStateRepository,
)

EventIdFactory = Callable[[], str]
Clock = Callable[[], datetime]


class SqlAlchemyExecutionRepository(SqlAlchemyProposalGateRepository):
    def __init__(
        self,
        session: Session,
        *,
        event_id_factory: EventIdFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        super().__init__(session)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._state_repository = SqlAlchemyTransactionStateRepository(
            session,
            event_id_factory=event_id_factory,
            clock=self._clock,
        )

    def claim_idempotency(
        self, record: IdempotencyRecord
    ) -> tuple[IdempotencyRecord, bool]:
        existing = self.get_idempotency(
            actor_id=record.actor_id,
            operation=record.operation,
            idempotency_key=record.idempotency_key,
        )
        if existing is not None:
            return existing, False

        values = {
            "id": record.id,
            "actor_id": record.actor_id,
            "operation": record.operation,
            "idempotency_key": record.idempotency_key,
            "request_fingerprint": record.request_fingerprint,
            "resource_type": record.resource_type,
            "resource_id": record.resource_id,
            "response_code": record.response_code,
            "response_body_hash": record.response_body_hash,
            "created_at": record.created_at,
        }
        dialect_name = self._session.get_bind().dialect.name
        if dialect_name == "postgresql":
            statement = (
                postgresql_insert(models.IdempotencyRecord)
                .values(**values)
                .on_conflict_do_nothing(
                    index_elements=["actor_id", "operation", "idempotency_key"]
                )
                .returning(models.IdempotencyRecord.id)
            )
        elif dialect_name == "sqlite":
            statement = (
                sqlite_insert(models.IdempotencyRecord)
                .values(**values)
                .on_conflict_do_nothing(
                    index_elements=["actor_id", "operation", "idempotency_key"]
                )
                .returning(models.IdempotencyRecord.id)
            )
        else:
            raise RuntimeError(f"unsupported idempotency dialect: {dialect_name}")
        inserted_id = self._session.scalar(statement)
        existing = self.get_idempotency(
            actor_id=record.actor_id,
            operation=record.operation,
            idempotency_key=record.idempotency_key,
        )
        if existing is None:
            raise RuntimeError("idempotency claim was neither inserted nor found")
        return existing, inserted_id == record.id

    def get_idempotency(
        self, *, actor_id: str, operation: str, idempotency_key: str
    ) -> IdempotencyRecord | None:
        record = self._session.scalar(
            select(models.IdempotencyRecord).where(
                models.IdempotencyRecord.actor_id == actor_id,
                models.IdempotencyRecord.operation == operation,
                models.IdempotencyRecord.idempotency_key == idempotency_key,
            )
        )
        return self._idempotency_to_domain(record) if record is not None else None

    def save_idempotency_result(
        self,
        record_id: str,
        *,
        resource_type: str,
        resource_id: str,
        response_code: int | None,
        response_body_hash: str | None,
    ) -> None:
        record = self._session.get(models.IdempotencyRecord, record_id)
        if record is None:
            raise LookupError(f"idempotency record {record_id} disappeared")
        record.resource_type = resource_type
        record.resource_id = resource_id
        record.response_code = response_code
        record.response_body_hash = response_body_hash
        self._session.flush()

    def lock_transaction(self, transaction_id: str) -> Transaction | None:
        record = self._session.scalar(
            select(models.Transaction)
            .where(models.Transaction.id == transaction_id)
            .with_for_update()
        )
        return self._transaction_to_domain(record) if record is not None else None

    def get_transaction(self, transaction_id: str) -> Transaction | None:
        record = self._session.get(models.Transaction, transaction_id)
        return self._transaction_to_domain(record) if record is not None else None

    def get_authorization(self, authorization_id: str) -> BuyerAuthorization | None:
        record = self._session.get(models.BuyerAuthorization, authorization_id)
        return self._authorization_to_domain(record) if record is not None else None

    def get_merchant_decision(self, decision_id: str) -> MerchantDecision | None:
        record = self._session.get(models.MerchantDecision, decision_id)
        return self._merchant_decision_to_domain(record) if record is not None else None

    def get_payment_attempt(self, transaction_id: str) -> PaymentAttempt | None:
        record = self._session.scalar(
            select(models.PaymentAttempt)
            .where(models.PaymentAttempt.transaction_id == transaction_id)
            .order_by(models.PaymentAttempt.attempt_number.desc())
            .limit(1)
        )
        return self._attempt_to_domain(record) if record is not None else None

    def add_payment_attempt(self, attempt: PaymentAttempt) -> None:
        self._session.add(
            models.PaymentAttempt(
                id=attempt.id,
                transaction_id=attempt.transaction_id,
                attempt_number=attempt.attempt_number,
                provider=attempt.provider.value,
                provider_request_fingerprint=attempt.provider_request_fingerprint,
                provider_order_id=attempt.provider_order_id,
                provider_payment_id=attempt.provider_payment_id,
                provider_order_state=attempt.provider_order_state,
                provider_payment_state=attempt.provider_payment_state,
                capture_state=attempt.capture_state,
                last_verified_at=attempt.last_verified_at,
                created_at=attempt.created_at,
                updated_at=attempt.updated_at,
            )
        )
        self._session.flush()

    def save_provider_observation(
        self, attempt_id: str, observation: ProviderObservation
    ) -> PaymentAttempt:
        record = self._session.get(models.PaymentAttempt, attempt_id)
        if record is None:
            raise LookupError(f"payment attempt {attempt_id} disappeared")
        record.provider_order_id = observation.provider_order_id
        record.provider_payment_id = observation.provider_payment_id
        record.provider_order_state = observation.provider_order_state
        record.provider_payment_state = observation.provider_payment_state
        record.capture_state = observation.capture_state
        record.last_verified_at = (
            observation.observed_at if observation.authenticity_verified else None
        )
        record.updated_at = self._clock()
        self._session.flush()
        return self._attempt_to_domain(record)

    def transition(
        self,
        transaction_id: str,
        new_state: TransactionState,
        *,
        actor_type: ActorType,
        actor_id: str | None,
        reason_code: str,
        correlation_id: str,
        provider_reference_redacted: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> Transaction:
        return self._state_repository.transition(
            transaction_id,
            new_state,
            actor_type=actor_type,
            actor_id=actor_id,
            reason_code=reason_code,
            correlation_id=correlation_id,
            provider_reference_redacted=provider_reference_redacted,
            metadata=metadata,
        ).transaction

    @staticmethod
    def _idempotency_to_domain(record: models.IdempotencyRecord) -> IdempotencyRecord:
        return IdempotencyRecord(
            id=record.id,
            actor_id=record.actor_id,
            operation=record.operation,
            idempotency_key=record.idempotency_key,
            request_fingerprint=record.request_fingerprint,
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            response_code=record.response_code,
            response_body_hash=record.response_body_hash,
            created_at=_as_utc(record.created_at),
        )

    @staticmethod
    def _attempt_to_domain(record: models.PaymentAttempt) -> PaymentAttempt:
        return PaymentAttempt(
            id=record.id,
            transaction_id=record.transaction_id,
            attempt_number=record.attempt_number,
            provider=ProviderName(record.provider),
            provider_request_fingerprint=record.provider_request_fingerprint,
            provider_order_id=record.provider_order_id,
            provider_payment_id=record.provider_payment_id,
            provider_order_state=record.provider_order_state,
            provider_payment_state=record.provider_payment_state,
            capture_state=record.capture_state,
            last_verified_at=(
                _as_utc(record.last_verified_at)
                if record.last_verified_at is not None
                else None
            ),
            created_at=_as_utc(record.created_at),
            updated_at=_as_utc(record.updated_at),
        )


class SqlAlchemyExecutionUnitOfWork:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        event_id_factory: EventIdFactory | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._event_id_factory = event_id_factory or (lambda: new_id("tevt"))
        self._clock = clock or (lambda: datetime.now(UTC))
        self._session: Session | None = None
        self.repository: ExecutionRepository

    def __enter__(self) -> "SqlAlchemyExecutionUnitOfWork":
        self._session = self._session_factory()
        self.repository = SqlAlchemyExecutionRepository(
            self._session,
            event_id_factory=self._event_id_factory,
            clock=self._clock,
        )
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._session is None:
            return
        try:
            if exc_type is None:
                self._session.commit()
            else:
                self._session.rollback()
        finally:
            self._session.close()
            self._session = None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
