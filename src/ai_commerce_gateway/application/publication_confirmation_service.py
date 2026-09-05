"""Publication-confirmation service (P0-5).

Issues dashboard-only confirmation tokens and verifies them before any
publication mutation, enforcing signature, expiry, issuer, audience and
one-time use via JTI replay protection.  Version drift protection comes
from the claim's ``expected_version`` plus the frozen service's own
version check: a publication increments the version, so an old token can
never publish twice.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

from ai_commerce_gateway.core.errors import AppError, ErrorCode
from ai_commerce_gateway.domain.publication_confirmation import (
    TOKEN_LIFETIME,
    PublicationConfirmationClaim,
    issue_publication_confirmation,
    verify_publication_confirmation,
)


class UsedConfirmationStore(Protocol):
    """Persistence seam for consumed confirmation JTIs."""

    def is_used(self, jti: str, now: datetime) -> bool:
        """Return True iff this JTI was already consumed (and is unexpired)."""
        ...

    def mark_used(
        self, jti: str, expires_at: datetime, *, merchant_id: str = "", product_id: str = ""
    ) -> None:
        """Record the JTI as consumed until its natural expiry."""
        ...


class InMemoryUsedConfirmationStore:
    """Tracks consumed JTIs so a token can be used exactly once.

    Entries are evicted once their token would have expired anyway.  Kept for
    tests; production wiring uses the durable SQLAlchemy store so replay
    protection survives restarts.
    """

    def __init__(self) -> None:
        self._used: dict[str, datetime] = {}

    def _evict(self, now: datetime) -> None:
        expired = [jti for jti, exp in self._used.items() if now > exp]
        for jti in expired:
            self._used.pop(jti, None)

    def is_used(self, jti: str, now: datetime) -> bool:
        self._evict(now)
        return jti in self._used

    def mark_used(
        self, jti: str, expires_at: datetime, *, merchant_id: str = "", product_id: str = ""
    ) -> None:
        self._used[jti] = expires_at


class PublicationConfirmationService:
    """Issues and verifies publication-confirmation tokens."""

    def __init__(
        self,
        secret: str,
        *,
        lifetime: timedelta = TOKEN_LIFETIME,
        used_store: UsedConfirmationStore | None = None,
    ) -> None:
        self._secret = secret
        self._lifetime = lifetime
        self._used = used_store or InMemoryUsedConfirmationStore()

    def issue(
        self,
        *,
        issuer_user_id: str,
        merchant_id: str,
        product_id: str,
        expected_version: int,
        action: str,
        now: datetime | None = None,
    ) -> tuple[str, datetime, str]:
        """Issue a signed publication-confirmation token.

        Returns ``(token_string, expires_at, jti)``.
        """
        return issue_publication_confirmation(
            issuer_user_id=issuer_user_id,
            merchant_id=merchant_id,
            product_id=product_id,
            expected_version=expected_version,
            action=action,
            secret=self._secret,
            now=now,
            lifetime=self._lifetime,
        )

    def verify(self, token: str, *, now: datetime | None = None) -> PublicationConfirmationClaim:
        """Verify the token and reject replayed JTIs.

        Note: marks nothing — the caller marks the JTI used only *after* a
        successful publication, so a failed publish does not burn the token
        while a successful one can never be replayed.
        """
        claim = verify_publication_confirmation(token, self._secret, now=now)
        check_time = now or datetime.now(tz=UTC)
        if self._used.is_used(claim.jti, check_time):
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "Publication confirmation token has already been used.",
                status_code=409,
            )
        return claim

    def mark_used(self, claim: PublicationConfirmationClaim) -> None:
        """Consume the token after a successful publication."""
        self._used.mark_used(
            claim.jti,
            claim.expires_at,
            merchant_id=claim.merchant_id,
            product_id=claim.product_id,
        )
