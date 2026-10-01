"""AC-10 / AD-R6: which pre-auths an insurer admin may override, and with what."""

import pytest

from src.domain.enums import PreAuthStatus as S
from src.domain.exceptions import BusinessRuleError
from src.domain.override_policy import ensure_override_allowed, is_overridable


@pytest.mark.ac("AC-10")
def test_ac10_auto_rejection_and_query_are_overridable() -> None:
    assert is_overridable(S.REJECTED, decided_by="SYSTEM")
    assert is_overridable(S.QUERY_RAISED, decided_by="SYSTEM")
    assert is_overridable(S.QUERY_RAISED, decided_by="adjudicator.priya")


@pytest.mark.ac("AC-10")
@pytest.mark.parametrize(("status", "by"), [(S.REJECTED, "adjudicator.priya"), (S.APPROVED, "SYSTEM"),
                                            (S.PARTIALLY_APPROVED, "SYSTEM"), (S.PENDING, "SYSTEM")])
def test_ac10_5_other_states_are_not_overridable(status: S, by: str) -> None:
    assert not is_overridable(status, decided_by=by)
    with pytest.raises(BusinessRuleError) as err:
        ensure_override_allowed(status, decided_by=by, target=S.APPROVED, reason="clinical review")
    assert err.value.code == "OVERRIDE_NOT_ALLOWED"


@pytest.mark.ac("AC-10")
@pytest.mark.parametrize("reason", ["", "   ", "\n"])
def test_ac10_4_reason_is_mandatory(reason: str) -> None:
    with pytest.raises(BusinessRuleError) as err:
        ensure_override_allowed(S.REJECTED, decided_by="SYSTEM", target=S.APPROVED, reason=reason)
    assert err.value.code == "OVERRIDE_REASON_REQUIRED"


@pytest.mark.ac("AC-10")
def test_ac10_reason_length_capped() -> None:
    with pytest.raises(BusinessRuleError):
        ensure_override_allowed(S.REJECTED, decided_by="SYSTEM", target=S.APPROVED, reason="x" * 501)


@pytest.mark.ac("AC-10")
@pytest.mark.parametrize("target", [S.REJECTED, S.QUERY_RAISED, S.PENDING])
def test_ac10_override_target_must_be_an_approval(target: S) -> None:
    with pytest.raises(BusinessRuleError):
        ensure_override_allowed(S.REJECTED, decided_by="SYSTEM", target=target, reason="ok")


@pytest.mark.ac("AC-10")
def test_ac10_allowed_override_returns_clean_reason() -> None:
    assert ensure_override_allowed(S.REJECTED, decided_by="SYSTEM", target=S.APPROVED,
                                   reason="  documented medical necessity ") == "documented medical necessity"
