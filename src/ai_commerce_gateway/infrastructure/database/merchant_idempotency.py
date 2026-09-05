"""SQLAlchemy implementation of catalog-mutation idempotency.

Reuses the shared ``idempotency_records`` table (see ``models.IdempotencyRecord``).
The atomic claim uses ``INSERT ... ON CONFLICT DO NOTHING`` backed by the
unique constraint ``(actor_id, operation, idempotency_key)`` so that
concurrent callers cannot double-execute a mutation.  The pattern mirrors
the transaction lane's ``SqlAlchemyExecutionRepository.claim_idempotency``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from ai_commerce_gateway.domain.idempotency import CatalogIdempotencyRecord
from ai_commerce_gateway.infrastructure.database import models

Clock = Callable[[], datetime]


class SqlAlchemyMerchantIdempotencyRepository:
    """Tenant-scoped idempotency persistence on the shared table."""

    def __init__(self, session: Session, *, clock: Clock | None = None) -> None:
        self._session = session
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    def get(
        self, *, actor_id: str, operation: str, idempotency_key: str
    ) -> CatalogIdempotencyRecord | None:
        record = self._session.scalar(
            select(models.IdempotencyRecord).where(
                models.IdempotencyRecord.actor_id == actor_id,
                models.IdempotencyRecord.operation == operation,
                models.IdempotencyRecord.idempotency_key == idempotency_key,
            )
        )
        return self._record_to_domain(record) if record is not None else None

    def claim(self, record: CatalogIdempotencyRecord) -> tuple[CatalogIdempotencyRecord, bool]:
        existing = self.get(
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
                .on_conflict_do_nothing(index_elements=["actor_id", "operation", "idempotency_key"])
                .returning(models.IdempotencyRecord.id)
            )
        elif dialect_name == "sqlite":
            statement = (
                sqlite_insert(models.IdempotencyRecord)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["actor_id", "operation", "idempotency_key"])
                .returning(models.IdempotencyRecord.id)
            )
        else:
            raise RuntimeError(f"unsupported idempotency dialect: {dialect_name}")

        inserted_id = self._session.scalar(statement)
        self._session.flush()

        existing = self.get(
            actor_id=record.actor_id,
            operation=record.operation,
            idempotency_key=record.idempotency_key,
        )
        if existing is None:
            raise RuntimeError("idempotency claim was neither inserted nor found")
        return existing, inserted_id == record.id

    def save_result(
        self,
        record_id: str,
        *,
        resource_type: str,
        resource_id: str,
        response_code: int,
        response_body_hash: str,
    ) -> None:
        record = self._session.get(models.IdempotencyRecord, record_id)
        if record is None:
            raise LookupError(f"idempotency record {record_id} disappeared")
        record.resource_type = resource_type
        record.resource_id = resource_id
        record.response_code = response_code
        record.response_body_hash = response_body_hash
        self._session.flush()

    @staticmethod
    def _record_to_domain(record: models.IdempotencyRecord) -> CatalogIdempotencyRecord:
        return CatalogIdempotencyRecord(
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


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
