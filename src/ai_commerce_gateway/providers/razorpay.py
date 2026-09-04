from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Final

import httpx

from ai_commerce_gateway.contracts.models import (
    CreateProviderOrderCommand,
    HandleWebhookCommand,
    ProviderLookupCommand,
    ProviderObservation,
    VerifyCheckoutCommand,
)
from ai_commerce_gateway.core.config import Settings
from ai_commerce_gateway.domain.enums import ProviderName

RAZORPAY_API_BASE_URL: Final = "https://api.razorpay.com"
RAZORPAY_CHECKOUT_SCRIPT_URL: Final = "https://checkout.razorpay.com/v1/checkout.js"
RAZORPAY_ORDER_PATH: Final = "/v1/orders"
_TEST_KEY_PREFIX: Final = "rzp_test_"
_ORDER_ID_PREFIX: Final = "order_"
_CREATED_ORDER_STATE: Final = "created"


class RazorpayAdapterError(RuntimeError):
    """Base error that never includes credentials or raw provider payloads."""


class RazorpayConfigurationError(RazorpayAdapterError):
    pass


class RazorpayRequestError(RazorpayAdapterError):
    pass


class RazorpayTransportError(RazorpayAdapterError):
    pass


class RazorpayApiError(RazorpayAdapterError):
    def __init__(self, status_code: int, provider_code: str | None) -> None:
        code = provider_code or "UNKNOWN"
        super().__init__(f"Razorpay rejected the request with HTTP {status_code} ({code}).")
        self.status_code = status_code
        self.provider_code = provider_code


class RazorpayProtocolError(RazorpayAdapterError):
    pass


@dataclass(frozen=True, slots=True)
class RazorpayCheckoutOptions:
    """Safe public fields required to open Razorpay Standard Checkout."""

    key: str
    amount: int
    currency: str
    order_id: str
    name: str
    description: str

    @property
    def script_url(self) -> str:
        return RAZORPAY_CHECKOUT_SCRIPT_URL

    def as_public_dict(self) -> dict[str, str | int]:
        return asdict(self)


class RazorpayAdapter:
    """Synchronous Test Mode adapter for order creation and checkout initiation.

    B4 intentionally performs exactly one create-order request and does not enable transport
    retries. Verification, webhooks and lookups remain unavailable until B5.
    """

    def __init__(
        self,
        *,
        key_id: str,
        key_secret: str,
        api_base_url: str = RAZORPAY_API_BASE_URL,
        timeout_seconds: float = 10.0,
        checkout_name: str = "AI Commerce Gateway",
        client: httpx.Client | None = None,
    ) -> None:
        _validate_configuration(
            key_id=key_id,
            key_secret=key_secret,
            api_base_url=api_base_url,
            timeout_seconds=timeout_seconds,
            checkout_name=checkout_name,
        )
        self._key_id = key_id
        self._key_secret = key_secret
        self._api_base_url = api_base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._checkout_name = checkout_name
        self._client = client or httpx.Client()
        self._owns_client = client is None

    @classmethod
    def from_settings(
        cls, settings: Settings, *, client: httpx.Client | None = None
    ) -> RazorpayAdapter:
        if settings.razorpay_key_id is None or settings.razorpay_key_secret is None:
            raise RazorpayConfigurationError("Razorpay Test Mode credentials are not configured.")
        return cls(
            key_id=settings.razorpay_key_id,
            key_secret=settings.razorpay_key_secret.get_secret_value(),
            api_base_url=settings.razorpay_api_base_url,
            timeout_seconds=settings.razorpay_timeout_seconds,
            checkout_name=settings.razorpay_checkout_name,
            client=client,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> RazorpayAdapter:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def create_order(self, command: CreateProviderOrderCommand) -> ProviderObservation:
        _validate_order_command(command)
        request_body: dict[str, Any] = {
            "amount": command.amount.amount_minor,
            "currency": command.amount.currency,
            "receipt": command.receipt,
            "partial_payment": False,
            "notes": {
                "transaction_id": command.transaction_id,
                "attempt_id": command.attempt_id,
                "request_fingerprint": command.request_fingerprint,
            },
        }
        try:
            response = self._client.post(
                f"{self._api_base_url}{RAZORPAY_ORDER_PATH}",
                json=request_body,
                auth=httpx.BasicAuth(self._key_id, self._key_secret),
                headers={"Accept": "application/json"},
                timeout=self._timeout_seconds,
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise RazorpayTransportError(
                "Razorpay order creation did not return a trustworthy response."
            ) from exc

        payload = _json_mapping(response)
        if not 200 <= response.status_code < 300:
            raise RazorpayApiError(response.status_code, _provider_error_code(payload))
        _validate_created_order(payload, command)
        return ProviderObservation(
            provider=ProviderName.RAZORPAY,
            provider_order_id=_required_string(payload, "id"),
            provider_payment_id=None,
            provider_order_state=_CREATED_ORDER_STATE,
            provider_payment_state=None,
            capture_state=None,
            authenticity_verified=False,
            observed_at=datetime.now(UTC),
            observation_source="razorpay_create_order_api",
        )

    def build_checkout_options(
        self,
        command: CreateProviderOrderCommand,
        observation: ProviderObservation,
        *,
        description: str = "Test Mode transaction",
    ) -> RazorpayCheckoutOptions:
        if (
            observation.provider is not ProviderName.RAZORPAY
            or observation.provider_order_state != _CREATED_ORDER_STATE
            or observation.provider_order_id is None
        ):
            raise RazorpayProtocolError(
                "Checkout requires a complete Razorpay created-order observation."
            )
        if not description or not description[0].isalnum():
            raise RazorpayRequestError("Checkout description must start with an alphanumeric.")
        return RazorpayCheckoutOptions(
            key=self._key_id,
            amount=command.amount.amount_minor,
            currency=command.amount.currency,
            order_id=observation.provider_order_id,
            name=self._checkout_name,
            description=description,
        )

    def verify_checkout(self, command: VerifyCheckoutCommand) -> ProviderObservation:
        raise NotImplementedError("Checkout verification belongs to phase B5.")

    def handle_webhook(self, command: HandleWebhookCommand) -> ProviderObservation:
        raise NotImplementedError("Webhook verification belongs to phase B5.")

    def lookup_order(self, command: ProviderLookupCommand) -> ProviderObservation:
        raise NotImplementedError("Provider lookup belongs to phase B5.")

    def lookup_payment(self, command: ProviderLookupCommand) -> ProviderObservation:
        raise NotImplementedError("Provider lookup belongs to phase B5.")


def _validate_configuration(
    *,
    key_id: str,
    key_secret: str,
    api_base_url: str,
    timeout_seconds: float,
    checkout_name: str,
) -> None:
    if not key_id.startswith(_TEST_KEY_PREFIX):
        raise RazorpayConfigurationError("B4 accepts Razorpay Test Mode keys only.")
    if not key_secret:
        raise RazorpayConfigurationError("Razorpay key secret is required.")
    if api_base_url != RAZORPAY_API_BASE_URL:
        raise RazorpayConfigurationError("Razorpay API base URL must use the approved HTTPS host.")
    if timeout_seconds <= 0:
        raise RazorpayConfigurationError("Razorpay timeout must be positive.")
    if not checkout_name.strip():
        raise RazorpayConfigurationError("Checkout business name is required.")


def _validate_order_command(command: CreateProviderOrderCommand) -> None:
    if command.amount.amount_minor <= 0:
        raise RazorpayRequestError("Razorpay order amount must be positive.")
    if len(command.receipt) > 40:
        raise RazorpayRequestError("Razorpay receipt must not exceed 40 characters.")
    for field_name, value in {
        "transaction_id": command.transaction_id,
        "attempt_id": command.attempt_id,
        "request_fingerprint": command.request_fingerprint,
    }.items():
        if not value or len(value) > 256:
            raise RazorpayRequestError(f"Razorpay note {field_name} is invalid.")


def _json_mapping(response: httpx.Response) -> Mapping[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise RazorpayProtocolError("Razorpay returned a non-JSON response.") from exc
    if not isinstance(payload, dict):
        raise RazorpayProtocolError("Razorpay returned an invalid JSON object.")
    return payload


def _provider_error_code(payload: Mapping[str, Any]) -> str | None:
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    return code if isinstance(code, str) and len(code) <= 128 else None


def _required_string(payload: Mapping[str, Any], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value:
        raise RazorpayProtocolError(f"Razorpay order field {field_name} is invalid.")
    return value


def _required_integer(payload: Mapping[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RazorpayProtocolError(f"Razorpay order field {field_name} is invalid.")
    return value


def _validate_created_order(
    payload: Mapping[str, Any], command: CreateProviderOrderCommand
) -> None:
    order_id = _required_string(payload, "id")
    if not order_id.startswith(_ORDER_ID_PREFIX):
        raise RazorpayProtocolError("Razorpay returned an invalid order identifier.")
    if _required_string(payload, "entity") != "order":
        raise RazorpayProtocolError("Razorpay returned an unexpected entity.")
    if _required_integer(payload, "amount") != command.amount.amount_minor:
        raise RazorpayProtocolError("Razorpay returned a mismatched order amount.")
    if _required_integer(payload, "amount_paid") != 0:
        raise RazorpayProtocolError("A newly created Razorpay order unexpectedly has paid funds.")
    if _required_integer(payload, "amount_due") != command.amount.amount_minor:
        raise RazorpayProtocolError("Razorpay returned a mismatched amount due.")
    if _required_string(payload, "currency") != command.amount.currency:
        raise RazorpayProtocolError("Razorpay returned a mismatched currency.")
    if payload.get("receipt") != command.receipt:
        raise RazorpayProtocolError("Razorpay returned a mismatched receipt.")
    if _required_string(payload, "status") != _CREATED_ORDER_STATE:
        raise RazorpayProtocolError("Razorpay did not return a newly created order.")
    if _required_integer(payload, "attempts") != 0:
        raise RazorpayProtocolError("A newly created Razorpay order has unexpected attempts.")
