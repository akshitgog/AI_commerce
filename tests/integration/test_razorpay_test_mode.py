from datetime import UTC, datetime
from time import monotonic, sleep

import pytest

from ai_commerce_gateway.contracts.models import (
    CreateProviderOrderCommand,
    Money,
    ProviderLookupCommand,
)
from ai_commerce_gateway.core.config import get_settings
from ai_commerce_gateway.domain.provider_verification import ProviderEvidence
from ai_commerce_gateway.providers.razorpay import (
    RazorpayAdapter,
    RazorpayProtocolError,
)


def eventually_lookup_order_by_receipt(
    adapter: RazorpayAdapter,
    command: CreateProviderOrderCommand,
    *,
    timeout_seconds: float = 10.0,
) -> ProviderEvidence:
    """Allow the Test Mode order-list index to become consistent after creation."""

    deadline = monotonic() + timeout_seconds
    while True:
        try:
            return adapter.lookup_order_by_receipt(command)
        except RazorpayProtocolError:
            if monotonic() >= deadline:
                raise
            sleep(0.25)


@pytest.mark.provider
def test_real_razorpay_test_mode_order_creation_and_lookup_when_configured() -> None:
    settings = get_settings()
    key_id = settings.razorpay_key_id
    key_secret = settings.razorpay_key_secret
    if key_id is None or key_secret is None:
        pytest.skip("razorpay.key_id/key_secret are not configured")

    unique = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    order_command = CreateProviderOrderCommand(
        transaction_id=f"txn_b4_{unique}",
        attempt_id=f"pay_b4_{unique}",
        amount=Money(amount_minor=100, currency="INR"),
        receipt=f"b4_{unique}"[:40],
        request_fingerprint=f"sha256:b4-{unique}",
    )
    with RazorpayAdapter(
        key_id=key_id,
        key_secret=key_secret.get_secret_value(),
    ) as adapter:
        observation = adapter.create_order(order_command)
        checkout = adapter.build_checkout_options(
            order_command,
            observation,
            description="B5 Test Mode lookup evidence",
        )
        lookup = adapter.lookup_order(
            ProviderLookupCommand(provider_order_id=observation.provider_order_id)
        )
        receipt_lookup = eventually_lookup_order_by_receipt(adapter, order_command)

    assert observation.provider_order_id is not None
    assert observation.provider_order_id.startswith("order_")
    assert observation.provider_order_state == "created"
    assert observation.provider_payment_id is None
    assert observation.provider_payment_state is None
    assert observation.capture_state is None
    assert checkout.order_id == observation.provider_order_id
    assert checkout.key.startswith("rzp_test_")
    assert lookup.provider_order_id == observation.provider_order_id
    assert lookup.provider_order_state == "created"
    assert lookup.provider_amount == order_command.amount
    assert receipt_lookup.provider_order_id == observation.provider_order_id
    assert receipt_lookup.provider_amount == order_command.amount
    print(
        f"Razorpay Test Mode order created and looked up: ...{observation.provider_order_id[-6:]}"
    )
