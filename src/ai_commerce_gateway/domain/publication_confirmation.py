"""Publication-confirmation token issuer and verifier.

A short-lived HMAC-SHA256 signed token that a dashboard must obtain
*before* an AI/MCP client can publish or unpublish a product.  The token
binds the actor, tenant, product, expected version and intended action
(publish|unpublish) and expires after a configurable window (default
5 minutes).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

from ai_commerce_gateway.core.errors import AppError, ErrorCode

_TOKEN_LIFETIME: Final[timedelta] = timedelta(minutes=5)


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


# ---------------------------------------------------------------------------
# Domain claim
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PublicationConfirmationClaim:
    """A decoded, verified publication-confirmation token."""

    actor_id: str
    merchant_id: str
    product_id: str
    version: int
    action: str  # "publish" | "unpublish"
    issued_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if self.action not in ("publish", "unpublish"):
            raise ValueError(f"Invalid action: {self.action!r}")
        for field_name in ("actor_id", "merchant_id", "product_id"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")
        if self.version < 1:
            raise ValueError("version must be >= 1")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def issue_publication_confirmation(
    *,
    actor_id: str,
    merchant_id: str,
    product_id: str,
    version: int,
    action: str,
    secret: str,
    now: datetime | None = None,
    lifetime: timedelta = _TOKEN_LIFETIME,
) -> tuple[str, datetime]:
    """Create and sign a publication-confirmation token.

    Returns ``(token_string, expires_at)``.
    """
    now = now or datetime.now(tz=UTC)
    expires_at = now + lifetime

    if action not in ("publish", "unpublish"):
        raise ValueError(f"Invalid action: {action!r}")
    for field_name, field_value in (
        ("actor_id", actor_id),
        ("merchant_id", merchant_id),
        ("product_id", product_id),
    ):
        if not field_value.strip():
            raise ValueError(f"{field_name} must not be empty")
    if version < 1:
        raise ValueError("version must be >= 1")

    payload_dict = {
        "actor_id": actor_id,
        "merchant_id": merchant_id,
        "product_id": product_id,
        "version": version,
        "action": action,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    payload_b64 = _b64url_encode(
        json.dumps(payload_dict, sort_keys=True, separators=(",", ":")).encode()
    )
    sig = _sign(payload_b64.encode(), secret)
    token = f"{payload_b64}.{_b64url_encode(sig)}"
    truncated_expires = datetime.fromtimestamp(
        int(expires_at.timestamp()), tz=UTC
    )
    return token, truncated_expires


def verify_publication_confirmation(
    token: str,
    secret: str,
    *,
    now: datetime | None = None,
) -> PublicationConfirmationClaim:
    """Verify and decode a publication-confirmation token.

    Raises ``AppError`` with ``VALIDATION_ERROR`` on any failure.
    """
    now = now or datetime.now(tz=UTC)

    parts = token.split(".")
    if len(parts) != 2:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "Invalid publication confirmation token format.",
            status_code=400,
        )

    payload_b64, sig_b64 = parts
    expected_sig = _sign(payload_b64.encode(), secret)
    actual_sig = _b64url_decode(sig_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "Publication confirmation token signature is invalid.",
            status_code=400,
        )

    try:
        payload_dict = json.loads(_b64url_decode(payload_b64))
    except Exception:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "Publication confirmation token payload is corrupt.",
            status_code=400,
        ) from None

    expires_at = datetime.fromtimestamp(payload_dict["exp"], tz=UTC)
    if now > expires_at:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "Publication confirmation token has expired.",
            status_code=400,
        )

    issued_at = datetime.fromtimestamp(payload_dict["iat"], tz=UTC)

    return PublicationConfirmationClaim(
        actor_id=payload_dict["actor_id"],
        merchant_id=payload_dict["merchant_id"],
        product_id=payload_dict["product_id"],
        version=payload_dict["version"],
        action=payload_dict["action"],
        issued_at=issued_at,
        expires_at=expires_at,
    )
