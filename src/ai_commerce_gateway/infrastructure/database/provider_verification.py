from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker

from ai_commerce_gateway.application.provider_verification import VerificationRepository
from ai_commerce_gateway.core.ids import new_id
from ai_commerce_gateway.domain.enums import ProviderName
from ai_commerce_gateway.domain.execution import PaymentAttempt
from ai_commerce_gateway.domain.provider_verification import ProviderWebhookReceipt
from ai_commerce_gateway.infrastructure.database import models
from ai_commerce_gateway.infrastructure.database.execution import SqlAlchemyExecutionRepository

EventIdFactory = Callable[[], str]
Clock = Callable[[], datetime]


class SqlAlchemyVerificationRepository(SqlAlchemyExecutionRepository):
    def find_payment_attempt(
        self,
        *,
        provider_order_id: str | None,
        provider_payment_id: str | None,
    ) -> PaymentAttempt | None:
        clauses = []
        if provider_order_id is not None:
            clauses.append(models.PaymentAttempt.provider_order_id == provider_order_id)
        if provider_payment_id is not None:
            clauses.append(models.PaymentAttempt.provider_payment_id == provider_payment_id)
        if not clauses:
            return None
        records = list(
            self._session.scalars(select(models.PaymentAttempt).where(or_(*clauses)).limit(2))
        )
        if len(records) > 1:
            raise RuntimeError("provider references resolve to different payment attempts")
        return self._attempt_to_domain(records[0]) if records else None

    def claim_webhook(self, receipt: ProviderWebhookReceipt) -> tuple[ProviderWebhookReceipt, bool]:
        existing = self._get_webhook(receipt.provider, receipt.provider_event_id)
        if existing is not None:
            return existing, False
        values = {
            "id": receipt.id,
            "provider": receipt.provider.value,
            "provider_event_id": receipt.provider_event_id,
            "signature_valid": True,
            "payload_hash": receipt.payload_hash,
            "transaction_id": receipt.transaction_id,
            "processing_status": receipt.processing_status,
            "received_at": receipt.received_at,
            "processed_at": receipt.processed_at,
        }
        dialect_name = self._session.get_bind().dialect.name
        if dialect_name == "postgresql":
            statement = (
                postgresql_insert(models.ProviderWebhook)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["provider", "provider_event_id"])
                .returning(models.ProviderWebhook.id)
            )
        elif dialect_name == "sqlite":
            statement = (
                sqlite_insert(models.ProviderWebhook)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["provider", "provider_event_id"])
                .returning(models.ProviderWebhook.id)
            )
        else:
            raise RuntimeError(f"unsupported webhook dialect: {dialect_name}")
        inserted_id = self._session.scalar(statement)
        stored = self._get_webhook(receipt.provider, receipt.provider_event_id)
        if stored is None:
            raise RuntimeError("webhook claim was neither inserted nor found")
        return stored, inserted_id == receipt.id

    def update_webhook(
        self,
        receipt_id: str,
        *,
        transaction_id: str | None,
        processing_status: str,
        processed_at: datetime | None,
    ) -> ProviderWebhookReceipt:
        record = self._session.get(models.ProviderWebhook, receipt_id)
        if record is None:
            raise LookupError(f"provider webhook {receipt_id} disappeared")
        record.transaction_id = transaction_id
        record.processing_status = processing_status
        record.processed_at = processed_at
        self._session.flush()
        return self._receipt_to_domain(record)

    def _get_webhook(
        self, provider: ProviderName, provider_event_id: str
    ) -> ProviderWebhookReceipt | None:
        record = self._session.scalar(
            select(models.ProviderWebhook).where(
                models.ProviderWebhook.provider == provider.value,
                models.ProviderWebhook.provider_event_id == provider_event_id,
            )
        )
        return self._receipt_to_domain(record) if record is not None else None

    @staticmethod
    def _receipt_to_domain(record: models.ProviderWebhook) -> ProviderWebhookReceipt:
        return ProviderWebhookReceipt(
            id=record.id,
            provider=ProviderName(record.provider),
            provider_event_id=record.provider_event_id,
            payload_hash=record.payload_hash,
            transaction_id=record.transaction_id,
            processing_status=record.processing_status,
            received_at=_as_utc(record.received_at),
            processed_at=(
                _as_utc(record.processed_at) if record.processed_at is not None else None
            ),
        )


class SqlAlchemyVerificationUnitOfWork:
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
        self.repository: VerificationRepository

    def __enter__(self) -> "SqlAlchemyVerificationUnitOfWork":
        self._session = self._session_factory()
        self.repository = SqlAlchemyVerificationRepository(
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
