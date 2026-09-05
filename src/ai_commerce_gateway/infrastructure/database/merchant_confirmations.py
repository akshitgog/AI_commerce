"""Durable publication-confirmation replay store (P0-5).

Persists consumed confirmation JTIs so a used token cannot be replayed after
a restart.  Expired rows are removed lazily on lookup; tokens only live five
minutes, so the table stays small.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai_commerce_gateway.infrastructure.database import models


class SqlAlchemyUsedConfirmationStore:
    """Database-backed ``UsedConfirmationStore`` (durable replay protection)."""

    def __init__(self, session: Session, *, clock: Callable[[], datetime] | None = None) -> None:
        self._session = session
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    def is_used(self, jti: str, now: datetime) -> bool:
        self._evict_expired(now)
        record = self._session.get(models.UsedConfirmationToken, jti)
        return record is not None

    def mark_used(
        self, jti: str, expires_at: datetime, *, merchant_id: str = "", product_id: str = ""
    ) -> None:
        now = self._clock()
        try:
            # Savepoint: a duplicate JTI must not roll back the caller's work.
            with self._session.begin_nested():
                self._session.add(
                    models.UsedConfirmationToken(
                        jti=jti,
                        merchant_id=merchant_id,
                        product_id=product_id,
                        expires_at=expires_at,
                        used_at=now,
                    )
                )
        except IntegrityError:
            # JTI already consumed — this call is idempotently complete.
            pass

    def _evict_expired(self, now: datetime) -> None:
        self._session.execute(
            delete(models.UsedConfirmationToken).where(
                models.UsedConfirmationToken.expires_at < now
            )
        )
