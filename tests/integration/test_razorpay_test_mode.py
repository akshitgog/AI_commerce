import os
from datetime import UTC, datetime

import pytest

from ai_commerce_gateway.contracts.models import (
    CreateProviderOrderCommand,
    Money,
    ProviderLookupCommand,
)
from ai_commerce_gateway.providers.razorpay import RazorpayAdapter


@pytest.mark.provider
def test_real_razorpay_test_mode_order_creation_and_lookup_when_configured() -> None:
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")
    if not key_id or not key_secret:
        pytest.skip("Razorpay Test Mode credentials are not configured")

    unique = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    order_command = CreateProviderOrderCommand(
        transaction_id=f"txn_b4_{unique}",
        attempt_id=f"pay_b4_{unique}",
        amount=Money(amount_minor=100, currency="INR"),
        receipt=f"b4_{unique}"[:40],
        request_fingerprint=f"sha256:b4-{unique}",
    )
    with RazorpayAdapter(key_id=key_id, key_secret=key_secret) as adapter:
        observation = adapter.create_order(order_command)
        checkout = adapter.build_checkout_options(
            order_command,
            observation,
            description="B5 Test Mode lookup evidence",
        )
        lookup = adapter.lookup_order(
            ProviderLookupCommand(provider_order_id=observation.provider_order_id)
        )

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
    print(
        f"Razorpay Test Mode order created and looked up: ...{observation.provider_order_id[-6:]}"
    )
