"""Publication-confirmation token issuer and verifier (P0-5).

A short-lived HMAC-SHA256 signed token that the merchant *dashboard* issues
after explicit human review.  A publication action (publish/unpublish)
requires this token, verified for:

  signature, expiry, issuer, audience, issuing user, merchant, product,
  expected version, action, and one-time use (JTI replay protection).

The token NEVER enters ``SetProductPublicationCommand`` — it is verified and
stripped at the transport layer before the frozen catalog service is called.
Because every publication increments the product version, a token bound to
version N becomes unusable the moment version N+1 exists.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

from ai_commerce_gateway.core.errors import AppError, ErrorCode

TOKEN_LIFETIME: Final[timedelta] = timedelta(minutes=5)
CONFIRMATION_ISSUER: Final[str] = "merchant-dashboard"
CONFIRMATION_AUDIENCE: Final[str] = "merchant-mcp-publication"
ACTION_PUBLISH: Final[str] = "PUBLISH"
ACTION_UNPUBLISH: Final[str] = "UNPUBLISH"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * padding)


def _sign(payload_bytes: bytes, secret: str) -> bytes:
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).digest()


def _reject(message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, message, status_code=400)


# ---------------------------------------------------------------------------
# Domain claim
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PublicationConfirmationClaim:
    """A decoded, verified publication-confirmation token."""

    jti: str
    issuer_user_id: str  # merchant user (sub)
    merchant_id: str
    product_id: str
    expected_version: int
    action: str  # "PUBLISH" | "UNPUBLISH"
    issued_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if self.action not in (ACTION_PUBLISH, ACTION_UNPUBLISH):
            raise ValueError(f"Invalid action: {self.action!r}")
        for field_name in ("jti", "issuer_user_id", "merchant_id", "product_id"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")
        if self.expected_version < 1:
            raise ValueError("expected_version must be >= 1")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def issue_publication_confirmation(
    *,
    issuer_user_id: str,
    merchant_id: str,
    product_id: str,
    expected_version: int,
    action: str,
    secret: str,
    now: datetime | None = None,
    lifetime: timedelta = TOKEN_LIFETIME,
) -> tuple[str, datetime, str]:
    """Create and sign a publication-confirmation token.

    Returns ``(token_string, expires_at, jti)``.
    """
    now = now or datetime.now(tz=UTC)
    expires_at = now + lifetime

    if action not in (ACTION_PUBLISH, ACTION_UNPUBLISH):
        raise ValueError(f"Invalid action: {action!r}")
    for field_name, field_value in (
        ("issuer_user_id", issuer_user_id),
        ("merchant_id", merchant_id),
        ("product_id", product_id),
    ):
        if not field_value.strip():
            raise ValueError(f"{field_name} must not be empty")
    if expected_version < 1:
        raise ValueError("expected_version must be >= 1")

    jti = f"pc_{secrets.token_urlsafe(16)}"
    payload_dict = {
        "iss": CONFIRMATION_ISSUER,
        "aud": CONFIRMATION_AUDIENCE,
        "jti": jti,
        "sub": issuer_user_id,
        "merchant_id": merchant_id,
        "product_id": product_id,
        "expected_version": expected_version,
        "action": action,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    payload_b64 = _b64url_encode(
        json.dumps(payload_dict, sort_keys=True, separators=(",", ":")).encode()
    )
    sig = _sign(payload_b64.encode(), secret)
    token = f"{payload_b64}.{_b64url_encode(sig)}"
    truncated_expires = datetime.fromtimestamp(int(expires_at.timestamp()), tz=UTC)
    return token, truncated_expires, jti


def verify_publication_confirmation(
    token: str,
    secret: str,
    *,
    now: datetime | None = None,
) -> PublicationConfirmationClaim:
    """Verify signature, expiry, issuer and audience; decode the claim."""
    now = now or datetime.now(tz=UTC)

    parts = token.split(".")
    if len(parts) != 2:
        raise _reject("Invalid publication confirmation token format.")

    payload_b64, sig_b64 = parts
    expected_sig = _sign(payload_b64.encode(), secret)
    actual_sig = _b64url_decode(sig_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise _reject("Publication confirmation token signature is invalid.")

    try:
        payload_dict = json.loads(_b64url_decode(payload_b64))
    except Exception:
        raise _reject("Publication confirmation token payload is corrupt.") from None

    if not isinstance(payload_dict, dict):
        raise _reject("Publication confirmation token payload is corrupt.")

    if payload_dict.get("iss") != CONFIRMATION_ISSUER:
        raise _reject("Publication confirmation token issuer is invalid.")
    if payload_dict.get("aud") != CONFIRMATION_AUDIENCE:
        raise _reject("Publication confirmation token audience is invalid.")

    try:
        expires_at = datetime.fromtimestamp(payload_dict["exp"], tz=UTC)
        issued_at = datetime.fromtimestamp(payload_dict["iat"], tz=UTC)
        claim = PublicationConfirmationClaim(
            jti=payload_dict["jti"],
            issuer_user_id=payload_dict["sub"],
            merchant_id=payload_dict["merchant_id"],
            product_id=payload_dict["product_id"],
            expected_version=payload_dict["expected_version"],
            action=payload_dict["action"],
            issued_at=issued_at,
            expires_at=expires_at,
        )
    except (KeyError, ValueError, TypeError):
        raise _reject("Publication confirmation token claims are invalid.") from None

    if now > expires_at:
        raise _reject("Publication confirmation token has expired.")

    return claim
