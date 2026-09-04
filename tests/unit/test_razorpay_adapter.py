import base64
import json
from collections.abc import Callable
from datetime import UTC

import httpx
import pytest

from ai_commerce_gateway.contracts.models import (
    CreateProviderOrderCommand,
    Money,
)
from ai_commerce_gateway.core.config import Settings
from ai_commerce_gateway.domain.enums import ProviderName
from ai_commerce_gateway.providers.razorpay import (
    RAZORPAY_CHECKOUT_SCRIPT_URL,
    RazorpayAdapter,
    RazorpayApiError,
    RazorpayConfigurationError,
    RazorpayProtocolError,
    RazorpayRequestError,
    RazorpayTransportError,
)

KEY_ID = "rzp_test_unit_key"
KEY_SECRET = "unit-secret-never-log"


def command(
    *, amount_minor: int = 50_000, receipt: str = "txn_test"
) -> CreateProviderOrderCommand:
    return CreateProviderOrderCommand(
        transaction_id="txn_test",
        attempt_id="pay_test",
        amount=Money(amount_minor=amount_minor, currency="INR"),
        receipt=receipt,
        request_fingerprint="sha256:provider-request",
    )


def created_order(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "order_test_123456",
        "entity": "order",
        "amount": 50_000,
        "amount_paid": 0,
        "amount_due": 50_000,
        "currency": "INR",
        "receipt": "txn_test",
        "offer_id": None,
        "status": "created",
        "attempts": 0,
        "notes": {},
        "created_at": 1_725_458_400,
    }
    payload.update(overrides)
    return payload


def client_for(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_create_order_sends_one_exact_test_mode_request_and_normalizes_evidence() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=created_order())

    with client_for(handler) as client:
        adapter = RazorpayAdapter(key_id=KEY_ID, key_secret=KEY_SECRET, client=client)
        observation = adapter.create_order(command())

    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://api.razorpay.com/v1/orders"
    expected_auth = base64.b64encode(f"{KEY_ID}:{KEY_SECRET}".encode()).decode()
    assert request.headers["Authorization"] == f"Basic {expected_auth}"
    assert json.loads(request.content) == {
        "amount": 50_000,
        "currency": "INR",
        "receipt": "txn_test",
        "partial_payment": False,
        "notes": {
            "transaction_id": "txn_test",
            "attempt_id": "pay_test",
            "request_fingerprint": "sha256:provider-request",
        },
    }
    assert observation.provider is ProviderName.RAZORPAY
    assert observation.provider_order_id == "order_test_123456"
    assert observation.provider_order_state == "created"
    assert observation.provider_payment_id is None
    assert observation.provider_payment_state is None
    assert observation.capture_state is None
    assert observation.authenticity_verified is False
    assert observation.observed_at.tzinfo is UTC
    assert observation.observation_source == "razorpay_create_order_api"


def test_checkout_options_contain_public_fields_and_never_the_secret() -> None:
    with client_for(lambda _: httpx.Response(200, json=created_order())) as client:
        adapter = RazorpayAdapter(key_id=KEY_ID, key_secret=KEY_SECRET, client=client)
        order_command = command()
        observation = adapter.create_order(order_command)
        options = adapter.build_checkout_options(
            order_command,
            observation,
            description="Demo transaction",
        )

    assert options.script_url == RAZORPAY_CHECKOUT_SCRIPT_URL
    assert options.as_public_dict() == {
        "key": KEY_ID,
        "amount": 50_000,
        "currency": "INR",
        "order_id": "order_test_123456",
        "name": "AI Commerce Gateway",
        "description": "Demo transaction",
    }
    assert KEY_SECRET not in json.dumps(options.as_public_dict())


@pytest.mark.parametrize(
    ("key_id", "key_secret", "api_base_url", "timeout", "name"),
    [
        ("rzp_live_forbidden", KEY_SECRET, "https://api.razorpay.com", 10.0, "Gateway"),
        ("not-a-key", KEY_SECRET, "https://api.razorpay.com", 10.0, "Gateway"),
        (KEY_ID, "", "https://api.razorpay.com", 10.0, "Gateway"),
        (KEY_ID, KEY_SECRET, "http://api.razorpay.com", 10.0, "Gateway"),
        (KEY_ID, KEY_SECRET, "https://example.test", 10.0, "Gateway"),
        (KEY_ID, KEY_SECRET, "https://api.razorpay.com", 0.0, "Gateway"),
        (KEY_ID, KEY_SECRET, "https://api.razorpay.com", 10.0, ""),
    ],
)
def test_configuration_fails_closed_outside_approved_test_mode(
    key_id: str,
    key_secret: str,
    api_base_url: str,
    timeout: float,
    name: str,
) -> None:
    with pytest.raises(RazorpayConfigurationError):
        RazorpayAdapter(
            key_id=key_id,
            key_secret=key_secret,
            api_base_url=api_base_url,
            timeout_seconds=timeout,
            checkout_name=name,
        )


@pytest.mark.parametrize(
    "order_command",
    [
        command(amount_minor=0),
        command(receipt="r" * 41),
        command().model_copy(update={"transaction_id": ""}),
        command().model_copy(update={"attempt_id": "a" * 257}),
        command().model_copy(update={"request_fingerprint": ""}),
    ],
)
def test_invalid_order_command_is_rejected_before_network_dispatch(
    order_command: CreateProviderOrderCommand,
) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=created_order())

    with client_for(handler) as client:
        adapter = RazorpayAdapter(key_id=KEY_ID, key_secret=KEY_SECRET, client=client)
        with pytest.raises(RazorpayRequestError):
            adapter.create_order(order_command)
    assert calls == 0


def test_api_rejection_is_sanitized_and_never_retried() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": "BAD_REQUEST_ERROR",
                    "description": "sensitive provider detail",
                }
            },
        )

    with client_for(handler) as client:
        adapter = RazorpayAdapter(key_id=KEY_ID, key_secret=KEY_SECRET, client=client)
        with pytest.raises(RazorpayApiError) as error:
            adapter.create_order(command())

    assert calls == 1
    assert error.value.status_code == 400
    assert error.value.provider_code == "BAD_REQUEST_ERROR"
    assert "sensitive provider detail" not in str(error.value)
    assert KEY_SECRET not in str(error.value)


def test_transport_timeout_is_uncertain_and_never_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timed out after dispatch", request=request)

    with client_for(handler) as client:
        adapter = RazorpayAdapter(key_id=KEY_ID, key_secret=KEY_SECRET, client=client)
        with pytest.raises(RazorpayTransportError):
            adapter.create_order(command())
    assert calls == 1


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not-json"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json=created_order(id="payment_not_order")),
        httpx.Response(200, json=created_order(entity="payment")),
        httpx.Response(200, json=created_order(amount=49_999)),
        httpx.Response(200, json=created_order(amount_paid=1)),
        httpx.Response(200, json=created_order(amount_due=49_999)),
        httpx.Response(200, json=created_order(currency="USD")),
        httpx.Response(200, json=created_order(receipt="other")),
        httpx.Response(200, json=created_order(status="attempted")),
        httpx.Response(200, json=created_order(attempts=1)),
    ],
)
def test_malformed_or_mismatched_success_response_fails_closed(
    response: httpx.Response,
) -> None:
    with client_for(lambda _: response) as client:
        adapter = RazorpayAdapter(key_id=KEY_ID, key_secret=KEY_SECRET, client=client)
        with pytest.raises(RazorpayProtocolError):
            adapter.create_order(command())


def test_checkout_requires_created_order_and_valid_description() -> None:
    with client_for(lambda _: httpx.Response(200, json=created_order())) as client:
        adapter = RazorpayAdapter(key_id=KEY_ID, key_secret=KEY_SECRET, client=client)
        observation = adapter.create_order(command())

        with pytest.raises(RazorpayProtocolError):
            adapter.build_checkout_options(
                command(),
                observation.model_copy(update={"provider_order_state": "paid"}),
            )
        with pytest.raises(RazorpayRequestError):
            adapter.build_checkout_options(command(), observation, description="!invalid")


def test_from_settings_requires_credentials_and_unwraps_secret_only_in_adapter() -> None:
    with pytest.raises(RazorpayConfigurationError):
        RazorpayAdapter.from_settings(
            Settings(razorpay_key_id=None, razorpay_key_secret=None)
        )

    settings = Settings(
        razorpay_key_id=KEY_ID,
        razorpay_key_secret=KEY_SECRET,
    )
    with client_for(lambda _: httpx.Response(200, json=created_order())) as client:
        adapter = RazorpayAdapter.from_settings(settings, client=client)
        assert adapter.create_order(command()).provider_order_id == "order_test_123456"
    assert KEY_SECRET not in repr(settings)
