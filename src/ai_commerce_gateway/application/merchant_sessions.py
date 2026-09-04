"""Server-trusted merchant session boundary (P0-2).

Routes NEVER trust client-supplied identity: no ``X-Merchant-User-Id``,
``X-Merchant-Roles``, ``merchant_id`` in the body, or role claims are read
from requests.  The only client credential is an opaque bearer token that
resolves server-side to a ``MerchantSession``; the ``ActorContext`` is built
exclusively from that session plus the merchant-membership record in the
database.

Credential verification (password/OAuth) is a pluggable authenticator seam:
the default development authenticator proves membership through the
``MerchantUserRepository`` (roles come from the database, never the caller).
A production authenticator drops in behind the same Protocol without touching
any route.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final, Protocol

from ai_commerce_gateway.application.catalog_audit import (
    CatalogAuditEvent,
    emit_catalog_audit,
)
from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.enums import ActorType, MerchantRole
from ai_commerce_gateway.domain.repositories import MerchantUserRepository

SESSION_TTL: Final[timedelta] = timedelta(hours=8)


class MerchantAuthenticationError(AppError):
    def __init__(self, message: str = "Invalid or expired merchant session.") -> None:
        super().__init__(ErrorCode.UNAUTHENTICATED, message, status_code=401)


@dataclass(frozen=True, slots=True)
class MerchantSession:
    """Server-side session record. Never constructed from client input."""

    token: str
    merchant_id: str
    user_id: str
    role: MerchantRole
    issued_at: datetime
    expires_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at


class MerchantSessionService(Protocol):
    """The single trust boundary for merchant request identity."""

    def issue(
        self, merchant_id: str, user_id: str, *, correlation_id: str = ""
    ) -> MerchantSession:
        """Create a session after server-side membership verification."""
        ...

    def resolve(self, token: str) -> MerchantSession | None:
        """Return the live session for an opaque token, or None."""
        ...

    def revoke(self, token: str, *, correlation_id: str = "") -> None:
        """Invalidate a session (logout)."""
        ...


class InMemoryMerchantSessionService:
    """Process-local session store.

    Tokens are server-minted (``secrets.token_urlsafe``), opaque and revocable.
    Roles are resolved from the authoritative ``MerchantUserRepository`` at
    issuance and re-checked against membership at resolve time, so a forged or
    tampered token can never inflate privileges.  Auth-boundary events are
    audited (issue / failed issue / revoke) with no token material logged.
    """

    def __init__(
        self,
        user_repo: MerchantUserRepository,
        *,
        store: dict[str, MerchantSession] | None = None,
        ttl: timedelta = SESSION_TTL,
        audit_emitter: Callable[[CatalogAuditEvent], None] | None = emit_catalog_audit,
    ) -> None:
        self._user_repo = user_repo
        # Shared, app-scoped store so sessions survive across requests while
        # each request binds its own repository/session.
        self._sessions: dict[str, MerchantSession] = store if store is not None else {}
        self._ttl = ttl
        self._audit_emitter = audit_emitter

    def _audit(
        self,
        *,
        action: str,
        merchant_id: str,
        user_id: str,
        correlation_id: str,
    ) -> None:
        if self._audit_emitter is None:
            return
        self._audit_emitter(
            CatalogAuditEvent(
                actor_id=user_id,
                actor_type=ActorType.MERCHANT_USER.value,
                action=action,
                merchant_id=merchant_id,
                target_type="session",
                target_id=user_id,
                correlation_id=correlation_id,
                causation=None,
                before=None,
                after=None,
                version_before=None,
                version_after=None,
                occurred_at=datetime.now(tz=UTC),
            )
        )

    def issue(
        self, merchant_id: str, user_id: str, *, correlation_id: str = ""
    ) -> MerchantSession:
        membership = self._user_repo.get(merchant_id, user_id)
        if membership is None:
            self._audit(
                action="session.issue_failed",
                merchant_id=merchant_id,
                user_id=user_id,
                correlation_id=correlation_id,
            )
            # Do not reveal whether the merchant or the user is unknown.
            raise MerchantAuthenticationError(
                "No such merchant user or membership."
            )
        now = datetime.now(tz=UTC)
        session = MerchantSession(
            token=f"msess_{secrets.token_urlsafe(32)}",
            merchant_id=merchant_id,
            user_id=user_id,
            role=membership.role,
            issued_at=now,
            expires_at=now + self._ttl,
        )
        self._sessions[session.token] = session
        self._audit(
            action="session.issue",
            merchant_id=merchant_id,
            user_id=user_id,
            correlation_id=correlation_id,
        )
        return session

    def resolve(self, token: str) -> MerchantSession | None:
        session = self._sessions.get(token)
        if session is None:
            return None
        if session.is_expired(datetime.now(tz=UTC)):
            self._sessions.pop(token, None)
            return None
        # Re-verify membership/roles against the repository so a revoked or
        # demoted user cannot keep elevated rights mid-session.
        membership = self._user_repo.get(session.merchant_id, session.user_id)
        if membership is None:
            self._sessions.pop(token, None)
            return None
        return MerchantSession(
            token=session.token,
            merchant_id=session.merchant_id,
            user_id=session.user_id,
            role=membership.role,
            issued_at=session.issued_at,
            expires_at=session.expires_at,
        )

    def revoke(self, token: str, *, correlation_id: str = "") -> None:
        session = self._sessions.pop(token, None)
        if session is not None:
            self._audit(
                action="session.revoke",
                merchant_id=session.merchant_id,
                user_id=session.user_id,
                correlation_id=correlation_id,
            )
