"""Publication-confirmation service for dashboard-issued tokens.

Issues and verifies short-lived HMAC-SHA256-signed confirmation tokens
that an AI/MCP client must present before publishing or unpublishing a
product.  The token binds actor, tenant, product, version and action.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Final

from ai_commerce_gateway.domain.publication_confirmation import (
    PublicationConfirmationClaim,
    issue_publication_confirmation,
    verify_publication_confirmation,
)

_TOKEN_LIFETIME: Final[timedelta] = timedelta(minutes=5)


class PublicationConfirmationService:
    """Issues and verifies publication-confirmation tokens."""

    def __init__(self, secret: str, *, lifetime: timedelta = _TOKEN_LIFETIME) -> None:
        self._secret = secret
        self._lifetime = lifetime

    def issue(
        self,
        *,
        actor_id: str,
        merchant_id: str,
        product_id: str,
        version: int,
        action: str,
        now: datetime | None = None,
    ) -> tuple[str, datetime]:
        """Issue a signed publication-confirmation token.

        Returns ``(token_string, expires_at)``.
        """
        return issue_publication_confirmation(
            actor_id=actor_id,
            merchant_id=merchant_id,
            product_id=product_id,
            version=version,
            action=action,
            secret=self._secret,
            now=now,
            lifetime=self._lifetime,
        )

    def verify(
        self, token: str, *, now: datetime | None = None
    ) -> PublicationConfirmationClaim:
        """Verify and decode a publication-confirmation token."""
        return verify_publication_confirmation(token, self._secret, now=now)
