"""Durable merchant session store (P0-2/P0-4).

Same trust rules as the in-memory variant: identity and roles come from the
membership repository, and only the SHA-256 hash of the opaque bearer token
is persisted — a database leak never exposes a live session.  Sessions
survive restarts; revocation and expiry are enforced on every resolve.
"""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai_commerce_gateway.application.merchant_sessions import (
    SESSION_TTL,
    MerchantAuthenticationError,
    MerchantSession,
)
from ai_commerce_gateway.domain.repositories import MerchantUserRepository
from ai_commerce_gateway.infrastructure.database import models


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class SqlAlchemyMerchantSessionService:
    """Database-backed ``MerchantSessionService`` (durable)."""

    def __init__(
        self,
        user_repo: MerchantUserRepository,
        session: Session,
        *,
        ttl: timedelta = SESSION_TTL,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._session = session
        self._ttl = ttl
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    def issue(self, merchant_id: str, user_id: str) -> MerchantSession:
        membership = self._user_repo.get(merchant_id, user_id)
        if membership is None:
            # Do not reveal whether the merchant or the user is unknown.
            raise MerchantAuthenticationError("No such merchant user or membership.")

        now = self._clock()
        token = f"msess_{secrets.token_urlsafe(32)}"
        # Session row IDs are internal (never a canonical entity), so they do
        # not consume a frozen EntityPrefix.
        record = models.MerchantSessionRecord(
            id=f"msess_{secrets.token_urlsafe(16)}",
            token_hash=_hash_token(token),
            merchant_id=merchant_id,
            user_id=user_id,
            role=membership.role.value,
            issued_at=now,
            expires_at=now + self._ttl,
            revoked_at=None,
        )
        self._session.add(record)
        self._session.flush()
        return MerchantSession(
            token=token,
            merchant_id=merchant_id,
            user_id=user_id,
            role=membership.role,
            issued_at=now,
            expires_at=now + self._ttl,
        )

    def resolve(self, token: str) -> MerchantSession | None:
        record = self._session.scalar(
            select(models.MerchantSessionRecord).where(
                models.MerchantSessionRecord.token_hash == _hash_token(token)
            )
        )
        if record is None:
            return None
        now = self._clock()
        expires_at = _as_utc(record.expires_at)
        if record.revoked_at is not None or now >= expires_at:
            return None
        # Re-verify membership/roles against the repository so a revoked or
        # demoted user cannot keep elevated rights mid-session.
        membership = self._user_repo.get(record.merchant_id, record.user_id)
        if membership is None:
            return None
        return MerchantSession(
            token=token,
            merchant_id=record.merchant_id,
            user_id=record.user_id,
            role=membership.role,
            issued_at=_as_utc(record.issued_at),
            expires_at=expires_at,
        )

    def revoke(self, token: str) -> None:
        record = self._session.scalar(
            select(models.MerchantSessionRecord).where(
                models.MerchantSessionRecord.token_hash == _hash_token(token)
            )
        )
        if record is not None and record.revoked_at is None:
            record.revoked_at = self._clock()
            self._session.flush()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
