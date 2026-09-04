from datetime import UTC, datetime

from fastapi.testclient import TestClient

from ai_commerce_gateway.api.app import create_app
from ai_commerce_gateway.contracts.models import (
    HandleWebhookCommand,
    Money,
    TransactionView,
    VerifyCheckoutCommand,
)
from ai_commerce_gateway.domain.enums import TransactionState
from ai_commerce_gateway.domain.provider_verification import WebhookProcessingResult
from ai_commerce_gateway.providers.razorpay import RazorpaySignatureError

NOW = datetime(2026, 9, 4, 17, 0, tzinfo=UTC)


class RecordingVerificationService:
    def __init__(self) -> None:
        self.checkout_command: VerifyCheckoutCommand | None = None
        self.webhook_command: HandleWebhookCommand | None = None
        self.webhook_event_id: str | None = None
        self.correlation_ids: list[str] = []
        self.error: Exception | None = None

    def verify_checkout(
        self, command: VerifyCheckoutCommand, *, correlation_id: str
    ) -> TransactionView:
        if self.error is not None:
            raise self.error
        self.checkout_command = command
        self.correlation_ids.append(correlation_id)
        return TransactionView(
            id=command.transaction_id,
            proposal_id="prop_callback",
            merchant_id="mer_callback",
            buyer_id="buy_callback",
            amount=Money(amount_minor=100, currency="INR"),
            state=TransactionState.VERIFYING,
            created_at=NOW,
            updated_at=NOW,
        )

    def handle_webhook(
        self,
        command: HandleWebhookCommand,
        *,
        provider_event_id: str,
        correlation_id: str,
    ) -> WebhookProcessingResult:
        if self.error is not None:
            raise self.error
        self.webhook_command = command
        self.webhook_event_id = provider_event_id
        self.correlation_ids.append(correlation_id)
        return WebhookProcessingResult(
            provider_event_id=provider_event_id,
            processing_status="PROCESSED",
            duplicate=False,
            transaction_id="txn_callback",
            transaction_state=TransactionState.SUCCEEDED,
        )


def client_for(service: RecordingVerificationService) -> TestClient:
    return TestClient(create_app(service))


def test_checkout_callback_maps_only_frozen_command_fields() -> None:
    service = RecordingVerificationService()
    response = client_for(service).post(
        "/checkout/razorpay/verify",
        headers={"X-Correlation-ID": "corr_checkout"},
        json={
            "transaction_id": "txn_callback",
            "razorpay_order_id": "order_callback",
            "razorpay_payment_id": "pay_callback",
            "razorpay_signature": "a" * 64,
        },
    )

    assert response.status_code == 200
    assert response.json()["state"] == "VERIFYING"
    assert service.checkout_command == VerifyCheckoutCommand(
        transaction_id="txn_callback",
        provider_order_id="order_callback",
        provider_payment_id="pay_callback",
        signature="a" * 64,
    )
    assert service.correlation_ids == ["corr_checkout"]


def test_checkout_callback_rejects_extra_trusted_fields() -> None:
    service = RecordingVerificationService()
    response = client_for(service).post(
        "/checkout/razorpay/verify",
        json={
            "transaction_id": "txn_callback",
            "razorpay_order_id": "order_callback",
            "razorpay_payment_id": "pay_callback",
            "razorpay_signature": "a" * 64,
            "state": "SUCCEEDED",
        },
    )
    assert response.status_code == 422
    assert service.checkout_command is None


def test_webhook_uses_exact_raw_body_signature_and_event_id_headers() -> None:
    service = RecordingVerificationService()
    raw_body = b'{"event":"payment.captured", "spacing":"preserved"}'
    response = client_for(service).post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Correlation-ID": "corr_webhook",
            "X-Razorpay-Signature": "b" * 64,
            "X-Razorpay-Event-Id": "event_callback",
        },
    )

    assert response.status_code == 200
    assert response.json()["processing_status"] == "PROCESSED"
    assert service.webhook_command == HandleWebhookCommand(
        raw_body=raw_body,
        signature="b" * 64,
    )
    assert service.webhook_event_id == "event_callback"
    assert service.correlation_ids == ["corr_webhook"]


def test_webhook_requires_signature_and_event_identity_headers() -> None:
    service = RecordingVerificationService()
    response = client_for(service).post(
        "/webhooks/razorpay",
        content=b"{}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert service.webhook_command is None


def test_provider_signature_failure_returns_sanitized_error_envelope() -> None:
    service = RecordingVerificationService()
    service.error = RazorpaySignatureError("sensitive-provider-detail")
    response = client_for(service).post(
        "/checkout/razorpay/verify",
        json={
            "transaction_id": "txn_callback",
            "razorpay_order_id": "order_callback",
            "razorpay_payment_id": "pay_callback",
            "razorpay_signature": "0" * 64,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "PROVIDER_ERROR",
        "message": "Provider signature verification failed.",
        "details": {},
    }
    assert "sensitive-provider-detail" not in response.text
