"""AC-07 settlement = min(final_bill, pre_auth + buffer) - deductible - co-pay; invariant >= 0."""

from decimal import Decimal

import pytest

from src.domain.exceptions import SettlementInvariantError
from src.domain.settlement_calculator import SettlementInput, assert_settlement_invariant, calculate_settlement

D = Decimal


def _calc(pre: str, buf: str, bill: str, ded: str, copay: str):  # type: ignore[no-untyped-def]
    return calculate_settlement(SettlementInput(D(pre), D(buf), D(bill), D(ded), D(copay)))


@pytest.mark.ac("AC-07")
def test_ac07_1_worked_example() -> None:
    b = _calc("100000.00", "10", "90000.00", "5000.00", "10")
    assert (b.cap, b.admissible, b.deductible_applied, b.copay, b.settlement_amount) == (
        D("110000.00"), D("90000.00"), D("5000.00"), D("8500.00"), D("76500.00"))


@pytest.mark.ac("AC-07")
def test_ac07_2_bill_above_cap_is_capped() -> None:
    b = _calc("100000.00", "10", "120000.00", "0.00", "0")
    assert (b.admissible, b.settlement_amount) == (D("110000.00"), D("110000.00"))


@pytest.mark.ac("AC-07")
def test_ac07_3_deductible_larger_than_bill_never_negative() -> None:
    b = _calc("100000.00", "10", "3000.00", "5000.00", "20")
    assert (b.deductible_applied, b.copay, b.settlement_amount) == (D("3000.00"), D("0.00"), D("0.00"))


@pytest.mark.ac("AC-07")
def test_ac07_4_copay_rounds_half_up() -> None:
    b = _calc("1000.00", "10", "1000.05", "0.00", "10")
    assert (b.copay, b.settlement_amount) == (D("100.01"), D("900.04"))


@pytest.mark.ac("AC-07")
def test_ac07_zero_buffer_full_bill() -> None:
    b = _calc("100000.00", "0", "100000.00", "0.00", "0")
    assert b.settlement_amount == D("100000.00")


@pytest.mark.ac("AC-07")
def test_ac07_full_copay_pays_nothing() -> None:
    assert _calc("5000.00", "0", "5000.00", "0.00", "100").settlement_amount == D("0.00")


@pytest.mark.ac("AC-07")
def test_ac07_5_float_input_raises_type_error() -> None:
    with pytest.raises(TypeError):
        calculate_settlement(SettlementInput(D("100.00"), D("10"), 90.0, D("0.00"), D("0")))  # type: ignore[arg-type]


@pytest.mark.ac("AC-07")
@pytest.mark.parametrize(("settlement", "admissible"), [(D("-0.01"), D("10.00")), (D("10.01"), D("10.00"))])
def test_ac07_invariant_guard_raises(settlement: Decimal, admissible: Decimal) -> None:
    with pytest.raises(SettlementInvariantError):
        assert_settlement_invariant(settlement, admissible)


@pytest.mark.ac("AC-07")
@pytest.mark.parametrize("bill", ["0.01", "4999.99", "5000.00", "5000.01", "109999.99", "110000.00", "999999.99"])
@pytest.mark.parametrize("copay", ["0", "10", "33.33", "100"])
def test_ac07_invariant_holds_across_grid(bill: str, copay: str) -> None:
    b = _calc("100000.00", "10", bill, "5000.00", copay)
    assert D("0.00") <= b.settlement_amount <= b.admissible <= b.cap
    assert b.settlement_amount + b.deductible_applied + b.copay == b.admissible
