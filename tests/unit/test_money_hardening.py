"""P0-3 adversarial money validation tests.

The ``Money`` contract DTO must accept ONLY integer minor units plus an
explicit uppercase ISO-4217 currency.  It must reject every loose or
implicit representation: bools, floats (including NaN/Infinity), numeric
strings, negative amounts and lowercase/missing currencies.
"""

import math

import pytest
from pydantic import ValidationError

from ai_commerce_gateway.contracts.models import Money


class TestMoneyAccepts:
    def test_valid_inr(self):
        m = Money(amount_minor=169900, currency="INR")
        assert m.amount_minor == 169900
        assert m.currency == "INR"

    def test_zero_amount_allowed(self):
        m = Money(amount_minor=0, currency="USD")
        assert m.amount_minor == 0


class TestMoneyRejectsAdversarial:
    """Every one of these must raise ValidationError — never coerce."""

    @pytest.mark.parametrize(
        "bad_amount",
        [
            True,  # bool is int subclass — must reject
            False,
            10.0,  # float, even integral
            1699.99,  # float
            math.nan,  # NaN
            math.inf,  # Infinity
            -math.inf,
            -1,  # negative
            -100,
            "100",  # numeric string
            "1699.99",
            "",  # empty string
            None,  # null
            [100],  # sequence
            {"amount": 100},  # mapping
        ],
    )
    def test_amount_minor_rejected(self, bad_amount):
        with pytest.raises(ValidationError):
            Money(amount_minor=bad_amount, currency="INR")

    @pytest.mark.parametrize(
        "bad_currency",
        [
            "inr",  # lowercase
            "Inr",
            "IN",  # too short
            "INRP",  # too long
            "123",  # digits
            "",  # empty (implicit currency)
            None,  # missing
            123,  # non-string
        ],
    )
    def test_currency_rejected(self, bad_currency):
        with pytest.raises(ValidationError):
            Money(amount_minor=100, currency=bad_currency)

    def test_missing_currency_rejected(self):
        with pytest.raises(ValidationError):
            Money(amount_minor=100)  # type: ignore[call-arg]

    def test_missing_amount_rejected(self):
        with pytest.raises(ValidationError):
            Money(currency="INR")  # type: ignore[call-arg]

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            Money(amount_minor=100, currency="INR", display="₹1.00")  # type: ignore[call-arg]

    def test_bool_via_json_rejected(self):
        with pytest.raises(ValidationError):
            Money.model_validate({"amount_minor": True, "currency": "INR"})

    def test_numeric_string_via_json_rejected(self):
        with pytest.raises(ValidationError):
            Money.model_validate({"amount_minor": "169900", "currency": "INR"})

    def test_float_via_json_rejected(self):
        with pytest.raises(ValidationError):
            Money.model_validate({"amount_minor": 1699.0, "currency": "INR"})
