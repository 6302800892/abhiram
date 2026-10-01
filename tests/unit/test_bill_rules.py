"""AC-06 bill cap: final_bill <= pre_auth_amount + buffer (ST-R1)."""

from decimal import Decimal

import pytest

from src.domain.bill_rules import bill_cap, bill_within_cap, ensure_bill_within_cap
from src.domain.exceptions import BusinessRuleError

D = Decimal


@pytest.mark.ac("AC-06")
def test_ac06_5_boundary_is_inclusive() -> None:
    assert bill_within_cap(D("100000.00"), D("10"), D("110000.00"))
    assert not bill_within_cap(D("100000.00"), D("10"), D("110000.01"))


@pytest.mark.ac("AC-06")
def test_ac06_6_zero_buffer_cap_equals_pre_auth_amount() -> None:
    assert bill_cap(D("100000.00"), D("0")) == D("100000.00")


@pytest.mark.ac("AC-06")
def test_ac06_cap_is_quantized_half_up() -> None:
    assert bill_cap(D("1000.05"), D("10")) == D("1100.06")  # 1100.055 -> 1100.06


@pytest.mark.ac("AC-06")
def test_ac06_ensure_raises_with_cap_details() -> None:
    with pytest.raises(BusinessRuleError) as err:
        ensure_bill_within_cap(D("100000.00"), D("10"), D("110000.01"))
    assert err.value.code == "BILL_EXCEEDS_CAP"
    assert err.value.details == {"cap": "110000.00", "final_bill": "110000.01"}


@pytest.mark.nfr("NFR-01")
def test_bill_rules_reject_float() -> None:
    with pytest.raises(TypeError):
        bill_within_cap(D("100.00"), D("10"), 100.0)  # type: ignore[arg-type]
