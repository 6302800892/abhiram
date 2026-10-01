"""Fixed-point money helpers (NFR-01). All monetary values are Decimal quantized to 0.01 HALF_UP."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from src.domain.exceptions import ValidationError

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
HUNDRED = Decimal("100")
MAX_MONEY = Decimal("1E13")  # NFR-01 bound: keeps quantize() inside Decimal precision


def quantize(value: Decimal) -> Decimal:
    """Round to cents with ROUND_HALF_UP (the single rounding rule of the platform)."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def require_decimal(*values: object) -> None:
    """Raise TypeError if any value is not a Decimal (floats are never accepted)."""
    for value in values:
        if not isinstance(value, Decimal):
            raise TypeError(f"money must be Decimal, got {type(value).__name__}")


def to_money(raw: str | int | Decimal) -> Decimal:
    """Parse an exact money amount (max 2 decimal places) from str/int/Decimal; floats are rejected."""
    if isinstance(raw, float) or isinstance(raw, bool):  # money-float-ok: rejects floats
        raise TypeError("money must not be a float; send a decimal string such as \"1250.50\"")
    try:
        value = raw if isinstance(raw, Decimal) else Decimal(str(raw).strip())
    except InvalidOperation as exc:
        raise ValidationError("INVALID_MONEY", f"not a valid amount: {raw!r}") from exc
    if not value.is_finite():
        raise ValidationError("INVALID_MONEY", "amount must be finite")
    if abs(value) >= MAX_MONEY:
        raise ValidationError("INVALID_MONEY", "amount is out of range")
    exponent = value.as_tuple().exponent
    if isinstance(exponent, int) and exponent < -2:
        raise ValidationError("INVALID_MONEY", "amount may have at most 2 decimal places")
    return quantize(value)


def to_percent(raw: str | int | Decimal) -> Decimal:
    """Parse a percentage (e.g. buffer_pct, copay_pct) exactly; floats are rejected."""
    if isinstance(raw, float) or isinstance(raw, bool):  # money-float-ok: rejects floats
        raise TypeError("percentages must not be floats")
    try:
        return raw if isinstance(raw, Decimal) else Decimal(str(raw).strip())
    except InvalidOperation as exc:
        raise ValidationError("INVALID_PERCENT", f"not a valid percentage: {raw!r}") from exc


def money_str(value: Decimal) -> str:
    """Canonical 2-decimal string used for JSON and SQLite TEXT storage."""
    return f"{quantize(value):.2f}"


def percent_of(amount: Decimal, pct: Decimal) -> Decimal:
    """amount × pct / 100, quantized to cents."""
    require_decimal(amount, pct)
    return quantize(amount * pct / HUNDRED)
