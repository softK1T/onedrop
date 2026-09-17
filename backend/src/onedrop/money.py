"""Money primitives. Amounts are integer minor units; floats are never used."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

MINOR_EXPONENT: dict[str, int] = {"PLN": 2, "EUR": 2, "USD": 2, "UAH": 2}

# Indicative static snapshot used only when no live rate source is configured.
# The rate actually applied is stored on every expense row, so historical
# reports never change when this table is updated.
STATIC_RATES_TO_PLN: dict[str, Decimal] = {
    "PLN": Decimal("1"),
    "EUR": Decimal("4.30"),
    "USD": Decimal("3.95"),
    "UAH": Decimal("0.096"),
}


class UnsupportedCurrencyError(ValueError):
    """Raised for a currency outside the supported set."""


def exponent(currency: str) -> int:
    try:
        return MINOR_EXPONENT[currency.upper()]
    except KeyError as exc:
        raise UnsupportedCurrencyError(f"unsupported currency: {currency}") from exc


def to_minor_units(amount: Decimal | int | str, currency: str) -> int:
    """Convert a decimal amount to integer minor units, half-up rounded."""
    scale = Decimal(10) ** exponent(currency)
    value = Decimal(str(amount))
    return int((value * scale).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def from_minor_units(amount_minor: int, currency: str) -> Decimal:
    scale = Decimal(10) ** exponent(currency)
    return (Decimal(amount_minor) / scale).quantize(Decimal(1).scaleb(-exponent(currency)))


def format_amount(amount_minor: int, currency: str) -> str:
    return f"{from_minor_units(amount_minor, currency)} {currency.upper()}"


def rate_between(source: str, target: str) -> Decimal | None:
    """Indicative rate source -> target, or None when it cannot be determined."""
    source_upper, target_upper = source.upper(), target.upper()
    if source_upper == target_upper:
        return Decimal("1")
    source_rate = STATIC_RATES_TO_PLN.get(source_upper)
    target_rate = STATIC_RATES_TO_PLN.get(target_upper)
    if source_rate is None or target_rate is None or target_rate == 0:
        return None
    return (source_rate / target_rate).quantize(Decimal("0.00000001"))


def convert_minor(
    amount_minor: int, source: str, target: str
) -> tuple[int | None, Decimal | None]:
    """Convert minor units between currencies.

    Returns `(converted_minor, rate)`. When no rate is available both values are
    `None` and the caller must still store the original amount.
    """
    rate = rate_between(source, target)
    if rate is None:
        return None, None
    try:
        source_exp = exponent(source)
        target_exp = exponent(target)
    except UnsupportedCurrencyError:
        return None, None
    amount = Decimal(amount_minor) / (Decimal(10) ** source_exp)
    converted = amount * rate
    scale = Decimal(10) ** target_exp
    minor = int((converted * scale).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return minor, rate
