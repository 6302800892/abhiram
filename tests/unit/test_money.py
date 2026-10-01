"""NFR-01: money is fixed-point Decimal, quantized to 0.01 HALF_UP, never float."""

from decimal import Decimal

import pytest

from src.domain.exceptions import ValidationError
from src.domain.money import ZERO, money_str, quantize, require_decimal, to_money


@pytest.mark.nfr("NFR-01")
def test_to_money_parses_strings_exactly() -> None:
    assert to_money("1000.05") == Decimal("1000.05")
    assert to_money("7") == Decimal("7.00")


@pytest.mark.nfr("NFR-01")
def test_to_money_rejects_float() -> None:
    with pytest.raises(TypeError):
        to_money(0.1)  # type: ignore[arg-type]


@pytest.mark.nfr("NFR-01")
def test_to_money_rejects_more_than_two_decimals() -> None:
    with pytest.raises(ValidationError):
        to_money("10.001")


@pytest.mark.nfr("NFR-01")
def test_quantize_rounds_half_up() -> None:
    assert quantize(Decimal("100.005")) == Decimal("100.01")
    assert quantize(Decimal("100.004")) == Decimal("100.00")


@pytest.mark.nfr("NFR-01")
def test_require_decimal_rejects_float_and_accepts_decimal() -> None:
    require_decimal(Decimal("1.00"), ZERO)
    with pytest.raises(TypeError):
        require_decimal(Decimal("1.00"), 2.5)  # type: ignore[arg-type]


@pytest.mark.nfr("NFR-01")
def test_money_str_always_two_places() -> None:
    assert money_str(Decimal("5")) == "5.00"
    assert money_str(Decimal("76500.0")) == "76500.00"


@pytest.mark.nfr("NFR-01")
def test_whole_number_integers_are_exact_money() -> None:
    assert to_money(40000) == Decimal("40000.00")
