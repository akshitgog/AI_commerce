import hashlib
import hmac
import json
from collections.abc import Callable

import httpx
import pytest

from ai_commerce_gateway.contracts.models import (
    HandleWebhookCommand,
    Money,
    ProviderLookupCommand,
    VerifyCheckoutCommand,
)
from ai_commerce_gateway.providers.razorpay import (
    RazorpayAdapter,
    RazorpayApiError,
    RazorpayConfigurationError,
    RazorpayProtocolError,
    RazorpayRequestError,
    RazorpaySignatureError,
    RazorpayTransportError,
)

KEY_ID = "rzp_test_verification_key"
KEY_SECRET = "api-secret"
WEBHOOK_SECRET = "independent-webhook-secret"
ORDER_ID = "order_verified_123"
PAYMENT_ID = "pay_verified_456"


def signature(message: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def client_for(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def adapter(
    *, client: httpx.Client | None = None, webhook_secret: str | None = None
) -> RazorpayAdapter:
    return RazorpayAdapter(
        key_id=KEY_ID,
        key_secret=KEY_SECRET,
        webhook_secret=webhook_secret,
        client=client,
    )


def payment(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": PAYMENT_ID,
        "entity": "payment",
        "order_id": ORDER_ID,
        "status": "captured",
        "captured": True,
        "amount": 50_000,
        "currency": "INR",
    }
    payload.update(overrides)
    return payload


def order(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": ORDER_ID,
        "entity": "order",
        "status": "paid",
        "amount": 50_000,
        "amount_paid": 50_000,
        "amount_due": 0,
        "currency": "INR",
        "attempts": 1,
    }
    payload.update(overrides)
    return payload


def webhook(event: str = "payment.captured", **payment_overrides: object) -> bytes:
    return json.dumps(
        {
            "entity": "event",
            "event": event,
            "created_at": 1_725_450_000,
            "payload": {"payment": {"entity": payment(**payment_overrides)}},
        },
        separators=(",", ":"),
    ).encode()


def webhook_command(raw_body: bytes) -> HandleWebhookCommand:
    return HandleWebhookCommand(
        raw_body=raw_body,
        signature=signature(raw_body, WEBHOOK_SECRET),
    )


def test_checkout_signature_uses_server_order_and_payment_ids() -> None:
    message = f"{ORDER_ID}|{PAYMENT_ID}".encode()
    observation = adapter().verify_checkout(
        VerifyCheckoutCommand(
            transaction_id="txn_verified",
            provider_order_id=ORDER_ID,
            provider_payment_id=PAYMENT_ID,
            signature=signature(message, KEY_SECRET),
        )
    )

    assert observation.authenticity_verified is True
    assert observation.provider_order_id == ORDER_ID
    assert observation.provider_payment_id == PAYMENT_ID
    assert observation.provider_payment_state is None
    assert observation.capture_state is None


@pytest.mark.parametrize(
    "change",
    [
        {"provider_order_id": "order_tampered"},
        {"provider_payment_id": "pay_tampered"},
        {"signature": "0" * 64},
        {"signature": "not-hex"},
    ],
)
def test_checkout_signature_tampering_fails(change: dict[str, str]) -> None:
    values = {
        "transaction_id": "txn_verified",
        "provider_order_id": ORDER_ID,
        "provider_payment_id": PAYMENT_ID,
        "signature": signature(f"{ORDER_ID}|{PAYMENT_ID}".encode(), KEY_SECRET),
    }
    values.update(change)
    with pytest.raises(RazorpaySignatureError):
        adapter().verify_checkout(VerifyCheckoutCommand(**values))


def test_webhook_signature_is_verified_before_json_parsing() -> None:
    raw_body = b"not-json"
    with pytest.raises(RazorpaySignatureError):
        adapter(webhook_secret=WEBHOOK_SECRET).handle_webhook(
            HandleWebhookCommand(
                raw_body=raw_body,
                signature="0" * 64,
            )
        )

    with pytest.raises(RazorpayProtocolError, match="valid JSON"):
        adapter(webhook_secret=WEBHOOK_SECRET).handle_webhook(webhook_command(raw_body))


def test_captured_webhook_returns_verified_payment_evidence() -> None:
    raw_body = webhook()
    observation = adapter(webhook_secret=WEBHOOK_SECRET).handle_webhook(webhook_command(raw_body))

    assert observation.authenticity_verified is True
    assert observation.provider_order_id == ORDER_ID
    assert observation.provider_payment_id == PAYMENT_ID
    assert observation.provider_payment_state == "captured"
    assert observation.capture_state == "captured"
    assert observation.observation_source == "razorpay_webhook:payment.captured"


def test_webhook_secret_is_distinct_and_required() -> None:
    raw_body = webhook()
    with pytest.raises(RazorpayConfigurationError, match="webhook secret"):
        adapter().handle_webhook(webhook_command(raw_body))

    wrong_secret_command = HandleWebhookCommand(
        raw_body=raw_body,
        signature=signature(raw_body, KEY_SECRET),
    )
    with pytest.raises(RazorpaySignatureError):
        adapter(webhook_secret=WEBHOOK_SECRET).handle_webhook(wrong_secret_command)


@pytest.mark.parametrize(
    "command",
    [
        HandleWebhookCommand(raw_body=b"", signature="0" * 64),
    ],
)
def test_invalid_webhook_envelope_is_rejected_before_verification(
    command: HandleWebhookCommand,
) -> None:
    with pytest.raises(RazorpayRequestError):
        adapter(webhook_secret=WEBHOOK_SECRET).handle_webhook(command)


def test_unsupported_signed_webhook_is_safely_ignored() -> None:
    raw_body = webhook("payment.refunded")
    observation = adapter(webhook_secret=WEBHOOK_SECRET).handle_webhook(webhook_command(raw_body))

    assert observation.authenticity_verified is True
    assert observation.provider_payment_id is None
    assert observation.observation_source == "razorpay_webhook_ignored:payment.refunded"


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "captured", "captured": False},
        {"status": "authorized", "captured": True},
        {"status": "unknown", "captured": False},
        {"entity": "order"},
        {"id": "wrong_payment"},
        {"order_id": "wrong_order"},
    ],
)
def test_inconsistent_webhook_payment_fails_closed(overrides: dict[str, object]) -> None:
    raw_body = webhook(**overrides)
    with pytest.raises((RazorpayProtocolError, RazorpayRequestError)):
        adapter(webhook_secret=WEBHOOK_SECRET).handle_webhook(webhook_command(raw_body))


def test_payment_lookup_maps_captured_truth_and_checks_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == f"/v1/payments/{PAYMENT_ID}"
        assert request.headers["Authorization"].startswith("Basic ")
        return httpx.Response(200, json=payment())

    with client_for(handler) as client:
        observation = adapter(client=client).lookup_payment(
            ProviderLookupCommand(
                provider_order_id=ORDER_ID,
                provider_payment_id=PAYMENT_ID,
            )
        )

    assert observation.provider_payment_state == "captured"
    assert observation.capture_state == "captured"
    assert observation.provider_amount == Money(amount_minor=50_000, currency="INR")
    assert observation.authenticity_verified is True


@pytest.mark.parametrize(
    ("status", "captured", "capture_state"),
    [
        ("created", False, "not_captured"),
        ("authorized", False, "not_captured"),
        ("captured", True, "captured"),
        ("refunded", True, "captured"),
        ("failed", False, "not_captured"),
    ],
)
def test_payment_lookup_maps_supported_states(
    status: str, captured: bool, capture_state: str
) -> None:
    with client_for(
        lambda _: httpx.Response(200, json=payment(status=status, captured=captured))
    ) as client:
        observation = adapter(client=client).lookup_payment(
            ProviderLookupCommand(provider_payment_id=PAYMENT_ID)
        )
    assert observation.provider_payment_state == status
    assert observation.capture_state == capture_state


def test_order_lookup_maps_paid_truth() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == f"/v1/orders/{ORDER_ID}"
        return httpx.Response(200, json=order())

    with client_for(handler) as client:
        observation = adapter(client=client).lookup_order(
            ProviderLookupCommand(provider_order_id=ORDER_ID)
        )
    assert observation.provider_order_state == "paid"
    assert observation.provider_amount == Money(amount_minor=50_000, currency="INR")
    assert observation.authenticity_verified is True


@pytest.mark.parametrize(
    "payload",
    [
        order(id="order_another"),
        order(entity="payment"),
        order(status="unknown"),
        order(amount=49_999),
        order(amount_paid=49_999),
        order(amount_due=1),
        order(currency="inr"),
        order(attempts=-1),
    ],
)
def test_order_lookup_mismatch_fails_closed(payload: dict[str, object]) -> None:
    with client_for(lambda _: httpx.Response(200, json=payload)) as client:
        with pytest.raises(RazorpayProtocolError):
            adapter(client=client).lookup_order(ProviderLookupCommand(provider_order_id=ORDER_ID))


@pytest.mark.parametrize(
    "payload",
    [
        payment(id="pay_another"),
        payment(order_id="order_another"),
        payment(status="captured", captured=False),
        payment(entity="order"),
        payment(amount=0),
        payment(currency="inr"),
    ],
)
def test_payment_lookup_mismatch_fails_closed(payload: dict[str, object]) -> None:
    with client_for(lambda _: httpx.Response(200, json=payload)) as client:
        with pytest.raises((RazorpayProtocolError, RazorpayRequestError)):
            adapter(client=client).lookup_payment(
                ProviderLookupCommand(
                    provider_order_id=ORDER_ID,
                    provider_payment_id=PAYMENT_ID,
                )
            )


def test_lookup_api_and_transport_errors_are_sanitized_and_not_retried() -> None:
    calls = 0

    def rejected(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": {"code": "BAD_REQUEST_ERROR"}})

    with client_for(rejected) as client:
        with pytest.raises(RazorpayApiError) as captured:
            adapter(client=client).lookup_order(ProviderLookupCommand(provider_order_id=ORDER_ID))
    assert calls == 1
    assert KEY_SECRET not in str(captured.value)

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("details must be hidden", request=request)

    with client_for(timeout) as client:
        with pytest.raises(RazorpayTransportError, match="trustworthy response"):
            adapter(client=client).lookup_payment(
                ProviderLookupCommand(provider_payment_id=PAYMENT_ID)
            )
