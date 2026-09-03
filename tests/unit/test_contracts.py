from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from ai_commerce_gateway.contracts.models import (
    ApproveAuthorizationCommand,
    CatalogSearchQuery,
    Money,
)


def test_money_requires_minor_units_and_iso_currency_shape() -> None:
    assert Money(amount_minor=50000, currency="INR").amount_minor == 50000
    with pytest.raises(ValidationError):
        Money(amount_minor=-1, currency="INR")
    with pytest.raises(ValidationError):
        Money(amount_minor=1, currency="inr")


def test_catalog_range_must_be_ordered() -> None:
    with pytest.raises(ValidationError):
        CatalogSearchQuery(merchant_id="mer_1", min_price_minor=20, max_price_minor=10)


def test_authorization_contract_is_explicitly_bounded() -> None:
    command = ApproveAuthorizationCommand(
        proposal_id="prop_1",
        proposal_hash="sha256:test",
        max_quantity=1,
        max_amount=Money(amount_minor=50000, currency="INR"),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        idempotency_key="approve-1",
    )
    assert command.max_amount.currency == "INR"
    assert command.max_quantity == 1


def test_contracts_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        Money(amount_minor=1, currency="INR", price=1)  # type: ignore[call-arg]
