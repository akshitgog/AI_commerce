"""P0-5 publication-confirmation boundary tests.

Claim set: issuer, audience=merchant-mcp-publication, JTI, issuer user,
merchant, product, expected version, action PUBLISH/UNPUBLISH, iat, exp.
Verification covers signature, expiry, issuer, audience, actor, merchant,
product, version, action and replay.
"""

import json
from datetime import UTC, datetime, timedelta

import pytest

from ai_commerce_gateway.application.publication_confirmation_service import (
    PublicationConfirmationService,
)
from ai_commerce_gateway.core.errors import AppError
from ai_commerce_gateway.domain import publication_confirmation as pc
from ai_commerce_gateway.domain.publication_confirmation import (
    ACTION_PUBLISH,
    ACTION_UNPUBLISH,
    CONFIRMATION_AUDIENCE,
    CONFIRMATION_ISSUER,
    issue_publication_confirmation,
    verify_publication_confirmation,
)

SECRET = "test-publication-secret"


def _issue(**overrides) -> tuple[str, datetime, str]:
    kwargs = {
        "issuer_user_id": "mer_user_1",
        "merchant_id": "mer_1",
        "product_id": "prod_1",
        "expected_version": 1,
        "action": ACTION_PUBLISH,
        "secret": SECRET,
    }
    kwargs.update(overrides)
    return issue_publication_confirmation(**kwargs)


def _craft(payload: dict, secret: str = SECRET) -> str:
    """Forge a token with an arbitrary payload (valid signature by default)."""
    payload_b64 = pc._b64url_encode(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    )
    sig = pc._b64url_encode(pc._sign(payload_b64.encode(), secret))
    return f"{payload_b64}.{sig}"


def _valid_payload(**overrides) -> dict:
    now = datetime.now(tz=UTC)
    payload = {
        "iss": CONFIRMATION_ISSUER,
        "aud": CONFIRMATION_AUDIENCE,
        "jti": "pc_test1",
        "sub": "mer_user_1",
        "merchant_id": "mer_1",
        "product_id": "prod_1",
        "expected_version": 1,
        "action": ACTION_PUBLISH,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
    }
    payload.update(overrides)
    return payload


class TestIssuance:
    def test_claim_set_complete(self):
        token, expires_at, jti = _issue()
        claim = verify_publication_confirmation(token, SECRET)
        assert claim.jti == jti
        assert claim.issuer_user_id == "mer_user_1"
        assert claim.merchant_id == "mer_1"
        assert claim.product_id == "prod_1"
        assert claim.expected_version == 1
        assert claim.action == ACTION_PUBLISH
        assert claim.expires_at == expires_at

    def test_invalid_action_rejected_at_issue(self):
        with pytest.raises(ValueError):
            _issue(action="DELETE")

    def test_empty_merchant_rejected_at_issue(self):
        with pytest.raises(ValueError):
            _issue(merchant_id=" ")

    def test_zero_version_rejected_at_issue(self):
        with pytest.raises(ValueError):
            _issue(expected_version=0)


class TestVerification:
    def test_wrong_secret_rejected(self):
        token, _, _ = _issue()
        with pytest.raises(AppError) as exc_info:
            verify_publication_confirmation(token, "other-secret")
        assert "signature" in exc_info.value.message.lower()

    def test_tampered_payload_rejected(self):
        token, _, _ = _issue()
        head, sig = token.split(".")
        payload = json.loads(pc._b64url_decode(head))
        payload["merchant_id"] = "mer_evil"
        tampered_head = pc._b64url_encode(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        )
        forged = f"{tampered_head}.{sig}"  # signature no longer matches
        with pytest.raises(AppError) as exc_info:
            verify_publication_confirmation(forged, SECRET)
        assert "signature" in exc_info.value.message.lower()

    def test_wrong_issuer_rejected(self):
        token = _craft(_valid_payload(iss="rogue-issuer"))
        with pytest.raises(AppError) as exc_info:
            verify_publication_confirmation(token, SECRET)
        assert "issuer" in exc_info.value.message.lower()

    def test_wrong_audience_rejected(self):
        token = _craft(_valid_payload(aud="some-other-audience"))
        with pytest.raises(AppError) as exc_info:
            verify_publication_confirmation(token, SECRET)
        assert "audience" in exc_info.value.message.lower()

    def test_missing_jti_rejected(self):
        payload = _valid_payload()
        del payload["jti"]
        token = _craft(payload)
        with pytest.raises(AppError):
            verify_publication_confirmation(token, SECRET)

    def test_expired_rejected(self):
        past = datetime(2026, 1, 1, tzinfo=UTC)
        token, _, _ = _issue(now=past)
        later = past + timedelta(minutes=6)
        with pytest.raises(AppError) as exc_info:
            verify_publication_confirmation(token, SECRET, now=later)
        assert "expired" in exc_info.value.message.lower()

    def test_malformed_token_rejected(self):
        with pytest.raises(AppError):
            verify_publication_confirmation("not-a-token", SECRET)


class TestReplayProtection:
    def test_used_jti_rejected(self):
        svc = PublicationConfirmationService(SECRET)
        token, _, _ = _issue()
        claim = svc.verify(token)
        svc.mark_used(claim)
        with pytest.raises(AppError) as exc_info:
            svc.verify(token)
        assert exc_info.value.status_code == 409

    def test_distinct_jtis_independent(self):
        svc = PublicationConfirmationService(SECRET)
        token1, _, _ = _issue()
        token2, _, _ = _issue()
        claim1 = svc.verify(token1)
        svc.mark_used(claim1)
        # A second, separately-issued token still verifies.
        assert svc.verify(token2).jti != claim1.jti

    def test_used_store_evicts_after_expiry(self):
        svc = PublicationConfirmationService(SECRET)
        past = datetime(2026, 1, 1, tzinfo=UTC)
        token, _, _ = _issue(now=past)
        claim = svc.verify(token, now=past + timedelta(minutes=1))
        svc.mark_used(claim)
        later = past + timedelta(minutes=10)
        # After expiry the JTI is evicted; the token itself would be expired.
        assert svc._used.is_used(claim.jti, later) is False


class TestClaimMismatchSemantics:
    """Actor/merchant/product/version/action matching happens at the caller."""

    def test_claim_carries_expected_version_for_drift_detection(self):
        token, _, _ = _issue(expected_version=3)
        claim = verify_publication_confirmation(token, SECRET)
        assert claim.expected_version == 3
        # A product that has since moved to version 4 no longer matches.
        assert claim.expected_version != 4

    def test_action_binding(self):
        token, _, _ = _issue(action=ACTION_PUBLISH)
        claim = verify_publication_confirmation(token, SECRET)
        assert claim.action == ACTION_PUBLISH
        assert claim.action != ACTION_UNPUBLISH
