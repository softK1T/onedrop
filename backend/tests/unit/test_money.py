"""Money representation: integer minor units, Decimal maths, no floats."""

from __future__ import annotations

from decimal import Decimal

import pytest

from onedrop.money import (
    UnsupportedCurrencyError,
    convert_minor,
    format_amount,
    from_minor_units,
    rate_between,
    to_minor_units,
)


def test_forty_five_pln_is_4500_minor_units() -> None:
    assert to_minor_units("45", "PLN") == 4500
    assert to_minor_units(Decimal("45.00"), "PLN") == 4500


def test_rounding_is_half_up() -> None:
    assert to_minor_units("12.345", "EUR") == 1235
    assert to_minor_units("12.344", "EUR") == 1234


def test_round_trip_keeps_exact_decimal() -> None:
    assert from_minor_units(4500, "PLN") == Decimal("45.00")
    assert from_minor_units(1, "USD") == Decimal("0.01")


def test_format_amount_is_human_readable() -> None:
    assert format_amount(4500, "pln") == "45.00 PLN"


def test_unsupported_currency_raises() -> None:
    with pytest.raises(UnsupportedCurrencyError):
        to_minor_units("10", "CHF")


def test_same_currency_rate_is_one() -> None:
    assert rate_between("PLN", "PLN") == Decimal("1")
    converted, rate = convert_minor(4500, "PLN", "PLN")
    assert converted == 4500
    assert rate == Decimal("1")


def test_conversion_returns_rate_used() -> None:
    converted, rate = convert_minor(1000, "EUR", "PLN")
    assert rate is not None
    assert converted == 4300


def test_missing_rate_does_not_block_saving() -> None:
    converted, rate = convert_minor(1000, "CHF", "PLN")
    assert converted is None
    assert rate is None


def test_no_float_arithmetic_in_conversion() -> None:
    converted, rate = convert_minor(12_345, "USD", "PLN")
    assert isinstance(converted, int)
    assert isinstance(rate, Decimal)
