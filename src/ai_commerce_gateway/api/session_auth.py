"""Server-trusted buyer session authentication (P0-3).

Buyer identity is NEVER accepted from request bodies, query parameters or
arbitrary headers such as ``X-Buyer-ID``. The only accepted buyer identity is
an HMAC-signed, expiring session token minted server-side:

* ``BuyerSessionService.issue`` mints a token for a buyer id. Minting is
  guarded by the configured issuer key (``buyer_sessions.issuer_key``); in a
  real deployment the identity provider/backoffice holds that key.
* ``BuyerSessionService.resolve`` verifies signature and expiry and returns
  the session claims; tampered, expired or foreign-secret tokens are rejected.
* The application middleware turns a verified token into an
  ``ActorContext(actor_type=BUYER)`` on ``request.state``.

No store is required: tokens are self-verifying via the configured HMAC
secret (itsdangerous URLSafeTimedSerializer, SHA-256, constant-time compare).
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import SecretStr

from ai_commerce_gateway.contracts.models import ActorContext
from ai_commerce_gateway.core.config import Settings
from ai_commerce_gateway.domain.enums import ActorType

_TOKEN_SALT = "buyer-session-v1"


@dataclass(frozen=True, slots=True)
class BuyerSessionClaims:
    """Verified contents of a buyer session token."""

    buyer_id: str
    issued_at: datetime
    expires_at: datetime


class BuyerSessionService:
    """Mints and verifies buyer session tokens (server-trusted identity)."""

    def __init__(self, secret: SecretStr, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("buyer session ttl_seconds must be positive")
        self._serializer = URLSafeTimedSerializer(
            secret_key=secret.get_secret_value(),
            salt=_TOKEN_SALT,
        )
        self._ttl_seconds = ttl_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> "BuyerSessionService | None":
        """Build from configuration, or None when session auth is not configured.

        Returning None keeps the service fail-closed: without a configured
        secret, buyer endpoints simply authenticate nobody (401 everywhere).
        """
        secret = settings.buyer_sessions_secret
        if secret is None:
            return None
        return cls(secret=secret, ttl_seconds=settings.buyer_sessions_ttl_seconds)

    def issue(self, buyer_id: str) -> tuple[str, BuyerSessionClaims]:
        """Mint a new session token for the buyer. Server-side only."""
        now = datetime.now(UTC)
        claims = BuyerSessionClaims(
            buyer_id=buyer_id,
            issued_at=now,
            expires_at=now + timedelta(seconds=self._ttl_seconds),
        )
        token = self._serializer.dumps({"buyer_id": buyer_id, "iat": now.isoformat()})
        return token, claims

    def resolve(self, token: str) -> BuyerSessionClaims | None:
        """Verify a session token; return claims or None when invalid."""
        try:
            payload = self._serializer.loads(token, max_age=self._ttl_seconds)
        except (BadSignature, SignatureExpired):
            return None
        buyer_id = payload.get("buyer_id")
        iat = payload.get("iat")
        if not isinstance(buyer_id, str) or not buyer_id or not isinstance(iat, str):
            return None
        try:
            issued_at = datetime.fromisoformat(iat)
        except ValueError:
            return None
        return BuyerSessionClaims(
            buyer_id=buyer_id,
            issued_at=issued_at,
            expires_at=issued_at + timedelta(seconds=self._ttl_seconds),
        )

    def actor_context(self, token: str, *, correlation_id: str) -> ActorContext | None:
        """Resolve a token directly to a server-trusted buyer ActorContext."""
        claims = self.resolve(token)
        if claims is None:
            return None
        return ActorContext(
            actor_id=claims.buyer_id,
            actor_type=ActorType.BUYER,
            correlation_id=correlation_id,
        )
