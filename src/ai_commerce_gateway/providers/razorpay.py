from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Final

import httpx

from ai_commerce_gateway.contracts.models import (
    CreateProviderOrderCommand,
    HandleWebhookCommand,
    Money,
    ProviderLookupCommand,
    ProviderObservation,
    VerifyCheckoutCommand,
)
from ai_commerce_gateway.core.config import Settings
from ai_commerce_gateway.domain.enums import ProviderName
from ai_commerce_gateway.domain.provider_verification import ProviderEvidence

RAZORPAY_API_BASE_URL: Final = "https://api.razorpay.com"
RAZORPAY_CHECKOUT_SCRIPT_URL: Final = "https://checkout.razorpay.com/v1/checkout.js"
RAZORPAY_ORDER_PATH: Final = "/v1/orders"
RAZORPAY_PAYMENT_PATH: Final = "/v1/payments"
_TEST_KEY_PREFIX: Final = "rzp_test_"
_ORDER_ID_PREFIX: Final = "order_"
_PAYMENT_ID_PREFIX: Final = "pay_"
_CREATED_ORDER_STATE: Final = "created"
_ORDER_STATES: Final = frozenset({"created", "attempted", "paid"})
_PAYMENT_STATES: Final = frozenset({"created", "authorized", "captured", "refunded", "failed"})
_SUPPORTED_WEBHOOK_EVENTS: Final = frozenset(
    {"payment.authorized", "payment.captured", "payment.failed", "order.paid"}
)
_MAX_WEBHOOK_BYTES: Final = 1_000_000


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


class RazorpaySignatureError(RazorpayAdapterError):
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

    Provider HTTP requests are single-dispatch operations with transport retries disabled.
    """

    def __init__(
        self,
        *,
        key_id: str,
        key_secret: str,
        webhook_secret: str | None = None,
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
        self._webhook_secret = webhook_secret
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
            webhook_secret=(
                settings.razorpay_webhook_secret.get_secret_value()
                if settings.razorpay_webhook_secret is not None
                else None
            ),
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

    def verify_checkout(self, command: VerifyCheckoutCommand) -> ProviderEvidence:
        _validate_reference(command.provider_order_id, _ORDER_ID_PREFIX, "order")
        _validate_reference(command.provider_payment_id, _PAYMENT_ID_PREFIX, "payment")
        if not command.transaction_id.strip():
            raise RazorpayRequestError("Checkout transaction identifier is required.")
        message = f"{command.provider_order_id}|{command.provider_payment_id}".encode()
        _verify_hmac(message, command.signature, self._key_secret, "checkout")
        return ProviderEvidence(
            provider=ProviderName.RAZORPAY,
            provider_order_id=command.provider_order_id,
            provider_payment_id=command.provider_payment_id,
            authenticity_verified=True,
            observed_at=datetime.now(UTC),
            observation_source="razorpay_checkout_signature",
        )

    def handle_webhook(self, command: HandleWebhookCommand) -> ProviderEvidence:
        if self._webhook_secret is None or not self._webhook_secret:
            raise RazorpayConfigurationError("Razorpay webhook secret is not configured.")
        if not command.raw_body or len(command.raw_body) > _MAX_WEBHOOK_BYTES:
            raise RazorpayRequestError("Razorpay webhook body size is invalid.")
        _verify_hmac(command.raw_body, command.signature, self._webhook_secret, "webhook")
        try:
            payload = json.loads(command.raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RazorpayProtocolError("Razorpay webhook body is not valid JSON.") from exc
        if not isinstance(payload, dict) or payload.get("entity") != "event":
            raise RazorpayProtocolError("Razorpay webhook is not an event object.")
        event_name = _required_string(payload, "event")
        if event_name not in _SUPPORTED_WEBHOOK_EVENTS:
            return ProviderEvidence(
                provider=ProviderName.RAZORPAY,
                authenticity_verified=True,
                observed_at=datetime.now(UTC),
                observation_source=f"razorpay_webhook_ignored:{event_name[:64]}",
            )
        payment = _webhook_payment(payload)
        observation = _payment_observation(
            payment,
            source=f"razorpay_webhook:{event_name}",
        )
        if event_name in {"payment.captured", "order.paid"} and (
            observation.provider_payment_state != "captured"
            or observation.capture_state != "captured"
        ):
            raise RazorpayProtocolError("Razorpay captured webhook has inconsistent payment state.")
        return observation

    def lookup_order(self, command: ProviderLookupCommand) -> ProviderEvidence:
        if command.provider_order_id is None:
            raise RazorpayRequestError("Razorpay order lookup requires an order identifier.")
        _validate_reference(command.provider_order_id, _ORDER_ID_PREFIX, "order")
        payload = self._get(f"{RAZORPAY_ORDER_PATH}/{command.provider_order_id}")
        order_id = _required_string(payload, "id")
        if order_id != command.provider_order_id or payload.get("entity") != "order":
            raise RazorpayProtocolError("Razorpay returned a mismatched order lookup.")
        order_state = _required_string(payload, "status")
        if order_state not in _ORDER_STATES:
            raise RazorpayProtocolError("Razorpay returned an unsupported order state.")
        amount = _required_integer(payload, "amount")
        amount_paid = _required_integer(payload, "amount_paid")
        amount_due = _required_integer(payload, "amount_due")
        if amount <= 0 or amount_paid < 0 or amount_due < 0 or amount_paid + amount_due != amount:
            raise RazorpayProtocolError("Razorpay returned inconsistent order money fields.")
        if order_state == "paid" and amount_due != 0:
            raise RazorpayProtocolError("Razorpay paid order still has an amount due.")
        currency = _required_string(payload, "currency")
        if len(currency) != 3 or not currency.isupper():
            raise RazorpayProtocolError("Razorpay returned an invalid order currency.")
        if _required_integer(payload, "attempts") < 0:
            raise RazorpayProtocolError("Razorpay returned an invalid order attempt count.")
        return ProviderEvidence(
            provider=ProviderName.RAZORPAY,
            provider_amount=Money(amount_minor=amount, currency=currency),
            provider_order_id=order_id,
            provider_order_state=order_state,
            authenticity_verified=True,
            observed_at=datetime.now(UTC),
            observation_source="razorpay_order_lookup",
        )

    def lookup_order_by_receipt(
        self, command: CreateProviderOrderCommand
    ) -> ProviderEvidence:
        """Recover an ambiguously-created order without dispatching a second order.

        This is an internal recovery capability rather than an addition to the frozen
        provider contract. The deterministic transaction receipt and request notes bind
        the discovered order to the durable payment attempt.
        """

        _validate_order_command(command)
        payload = self._get(
            RAZORPAY_ORDER_PATH,
            params={"receipt": command.receipt, "count": "100"},
        )
        if payload.get("entity") != "collection":
            raise RazorpayProtocolError("Razorpay returned an invalid order collection.")
        items = payload.get("items")
        if not isinstance(items, list):
            raise RazorpayProtocolError("Razorpay returned an invalid order collection.")

        matches: list[Mapping[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                raise RazorpayProtocolError("Razorpay returned an invalid order entry.")
            if item.get("receipt") == command.receipt:
                matches.append(item)
        if len(matches) != 1:
            raise RazorpayProtocolError(
                "Razorpay receipt lookup did not identify exactly one trustworthy order."
            )

        order = matches[0]
        _validate_recovered_order(order, command)
        return _order_observation(order, source="razorpay_order_receipt_lookup")

    def lookup_payment(self, command: ProviderLookupCommand) -> ProviderEvidence:
        if command.provider_payment_id is None:
            raise RazorpayRequestError("Razorpay payment lookup requires a payment identifier.")
        _validate_reference(command.provider_payment_id, _PAYMENT_ID_PREFIX, "payment")
        payload = self._get(f"{RAZORPAY_PAYMENT_PATH}/{command.provider_payment_id}")
        observation = _payment_observation(payload, source="razorpay_payment_lookup")
        if observation.provider_payment_id != command.provider_payment_id:
            raise RazorpayProtocolError("Razorpay returned a mismatched payment lookup.")
        if (
            command.provider_order_id is not None
            and observation.provider_order_id != command.provider_order_id
        ):
            raise RazorpayProtocolError("Razorpay payment belongs to another order.")
        return observation

    def _get(
        self, path: str, *, params: Mapping[str, str] | None = None
    ) -> Mapping[str, Any]:
        try:
            response = self._client.get(
                f"{self._api_base_url}{path}",
                auth=httpx.BasicAuth(self._key_id, self._key_secret),
                headers={"Accept": "application/json"},
                params=params,
                timeout=self._timeout_seconds,
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise RazorpayTransportError(
                "Razorpay lookup did not return a trustworthy response."
            ) from exc
        payload = _json_mapping(response)
        if not 200 <= response.status_code < 300:
            raise RazorpayApiError(response.status_code, _provider_error_code(payload))
        return payload


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
        raise RazorpayProtocolError(f"Razorpay field {field_name} is invalid.")
    return value


def _required_boolean(payload: Mapping[str, Any], field_name: str) -> bool:
    value = payload.get(field_name)
    if not isinstance(value, bool):
        raise RazorpayProtocolError(f"Razorpay field {field_name} is invalid.")
    return value


def _validate_reference(value: str, prefix: str, label: str) -> None:
    if not value.startswith(prefix) or len(value) > 255:
        raise RazorpayRequestError(f"Razorpay {label} identifier is invalid.")


def _verify_hmac(message: bytes, signature: str, secret: str, label: str) -> None:
    is_hex = all(character in "0123456789abcdefABCDEF" for character in signature)
    if len(signature) != 64 or not is_hex:
        raise RazorpaySignatureError(f"Razorpay {label} signature is invalid.")
    expected = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature.lower()):
        raise RazorpaySignatureError(f"Razorpay {label} signature is invalid.")


def _webhook_payment(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    webhook_payload = payload.get("payload")
    if not isinstance(webhook_payload, dict):
        raise RazorpayProtocolError("Razorpay webhook payload is invalid.")
    payment_wrapper = webhook_payload.get("payment")
    if not isinstance(payment_wrapper, dict):
        raise RazorpayProtocolError("Razorpay webhook payment is missing.")
    payment = payment_wrapper.get("entity")
    if not isinstance(payment, dict):
        raise RazorpayProtocolError("Razorpay webhook payment entity is invalid.")
    return payment


def _payment_observation(payload: Mapping[str, Any], *, source: str) -> ProviderEvidence:
    payment_id = _required_string(payload, "id")
    _validate_reference(payment_id, _PAYMENT_ID_PREFIX, "payment")
    if payload.get("entity") != "payment":
        raise RazorpayProtocolError("Razorpay returned an unexpected payment entity.")
    order_id = _required_string(payload, "order_id")
    _validate_reference(order_id, _ORDER_ID_PREFIX, "order")
    payment_state = _required_string(payload, "status")
    if payment_state not in _PAYMENT_STATES:
        raise RazorpayProtocolError("Razorpay returned an unsupported payment state.")
    captured = _required_boolean(payload, "captured")
    if payment_state == "captured" and not captured:
        raise RazorpayProtocolError("Razorpay returned inconsistent capture fields.")
    if payment_state in {"created", "authorized", "failed"} and captured:
        raise RazorpayProtocolError("Razorpay returned inconsistent capture fields.")
    if _required_integer(payload, "amount") <= 0:
        raise RazorpayProtocolError("Razorpay returned an invalid payment amount.")
    currency = _required_string(payload, "currency")
    if len(currency) != 3 or not currency.isupper():
        raise RazorpayProtocolError("Razorpay returned an invalid payment currency.")
    return ProviderEvidence(
        provider=ProviderName.RAZORPAY,
        provider_amount=Money(
            amount_minor=_required_integer(payload, "amount"),
            currency=currency,
        ),
        provider_order_id=order_id,
        provider_payment_id=payment_id,
        provider_payment_state=payment_state,
        capture_state="captured" if captured else "not_captured",
        authenticity_verified=True,
        observed_at=datetime.now(UTC),
        observation_source=source,
    )


def _required_integer(payload: Mapping[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise RazorpayProtocolError(f"Razorpay field {field_name} is invalid.")
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


def _validate_recovered_order(
    payload: Mapping[str, Any], command: CreateProviderOrderCommand
) -> None:
    if payload.get("entity") != "order":
        raise RazorpayProtocolError("Razorpay returned an unexpected receipt lookup entity.")
    order_id = _required_string(payload, "id")
    _validate_reference(order_id, _ORDER_ID_PREFIX, "order")
    if _required_integer(payload, "amount") != command.amount.amount_minor:
        raise RazorpayProtocolError("Razorpay returned a mismatched recovered order amount.")
    if _required_string(payload, "currency") != command.amount.currency:
        raise RazorpayProtocolError("Razorpay returned a mismatched recovered order currency.")
    if payload.get("receipt") != command.receipt:
        raise RazorpayProtocolError("Razorpay returned a mismatched recovered order receipt.")
    order_state = _required_string(payload, "status")
    if order_state not in _ORDER_STATES:
        raise RazorpayProtocolError("Razorpay returned an unsupported recovered order state.")
    amount = _required_integer(payload, "amount")
    amount_paid = _required_integer(payload, "amount_paid")
    amount_due = _required_integer(payload, "amount_due")
    if amount_paid < 0 or amount_due < 0 or amount_paid + amount_due != amount:
        raise RazorpayProtocolError("Razorpay returned inconsistent recovered order money fields.")
    notes = payload.get("notes")
    if not isinstance(notes, dict):
        raise RazorpayProtocolError("Razorpay recovered order notes are invalid.")
    expected_notes = {
        "transaction_id": command.transaction_id,
        "attempt_id": command.attempt_id,
        "request_fingerprint": command.request_fingerprint,
    }
    if any(notes.get(key) != value for key, value in expected_notes.items()):
        raise RazorpayProtocolError("Razorpay recovered order is not bound to this attempt.")


def _order_observation(payload: Mapping[str, Any], *, source: str) -> ProviderEvidence:
    return ProviderEvidence(
        provider=ProviderName.RAZORPAY,
        provider_amount=Money(
            amount_minor=_required_integer(payload, "amount"),
            currency=_required_string(payload, "currency"),
        ),
        provider_order_id=_required_string(payload, "id"),
        provider_order_state=_required_string(payload, "status"),
        authenticity_verified=True,
        observed_at=datetime.now(UTC),
        observation_source=source,
    )
