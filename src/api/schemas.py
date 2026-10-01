"""Request models. Money fields accept decimal strings or integers only — floats are rejected (NFR-01)."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from src.domain.exceptions import MediCardError
from src.domain.money import to_money, to_percent


def _money(value: object) -> Decimal:
    if isinstance(value, float):
        raise ValueError("money must be a decimal string such as \"1250.50\", not a JSON number with a fraction")
    try:
        return to_money(value)  # type: ignore[arg-type]
    except (MediCardError, TypeError) as exc:
        raise ValueError(str(exc)) from exc


def _percent(value: object) -> Decimal:
    if isinstance(value, float):
        raise ValueError("percent must be a decimal string, not a float")
    try:
        return to_percent(value)  # type: ignore[arg-type]
    except (MediCardError, TypeError) as exc:
        raise ValueError(str(exc)) from exc


Money = Annotated[Decimal, BeforeValidator(_money)]
Percent = Annotated[Decimal, BeforeValidator(_percent)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginRequest(StrictModel):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=200)


class RegisterRequest(StrictModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=200)
    full_name: str = Field(min_length=1, max_length=120)


class LinkPolicyRequest(StrictModel):
    policy_number: str = Field(min_length=1, max_length=40)
    member_id: str = Field(min_length=1, max_length=40)
    date_of_birth: dt.date


class EligibilityRequest(StrictModel):
    member_id: str = Field(min_length=1, max_length=40)
    policy_number: str = Field(min_length=1, max_length=40)


class HospitalCreate(StrictModel):
    code: str = Field(min_length=3, max_length=12)
    name: str = Field(min_length=1, max_length=120)
    city: str = Field(min_length=1, max_length=80)
    in_network: bool = True


class HospitalPatch(StrictModel):
    in_network: bool


class ProductCreate(StrictModel):
    code: str = Field(min_length=2, max_length=20, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=1, max_length=120)
    sum_insured: Money
    annual_premium: Money


class PreAuthCreate(StrictModel):
    member_id: str = Field(min_length=1, max_length=40)
    policy_number: str = Field(min_length=1, max_length=40)
    diagnosis_code: str = Field(min_length=1, max_length=12)
    estimated_cost: Money
    expected_admission_date: dt.date
    clinical_notes: str | None = Field(default=None, max_length=2000)


class QueryResponse(StrictModel):
    response_note: str = Field(min_length=1, max_length=1000)


class DecisionCreate(StrictModel):
    status: Literal["APPROVED", "PARTIALLY_APPROVED", "REJECTED", "QUERY_RAISED"]
    approved_amount: Money | None = None
    reason_codes: list[str] = Field(min_length=1, max_length=10)
    note: str | None = Field(default=None, max_length=1000)


class OverrideRequest(StrictModel):
    status: Literal["APPROVED", "PARTIALLY_APPROVED"]
    approved_amount: Money | None = None
    reason: str = Field(max_length=1000)  # blank/too long is a business error (OVERRIDE_REASON_REQUIRED)


class AdmitRequest(StrictModel):
    admitted_on: dt.date


class DischargeRequest(StrictModel):
    discharged_on: dt.date


class ProcedureCreate(StrictModel):
    procedure_code: str = Field(min_length=1, max_length=20)
    description: str = Field(min_length=1, max_length=300)


class FinalBillCreate(StrictModel):
    amount: Money


class DisputeRequest(StrictModel):
    reason: str = Field(min_length=1, max_length=500)


class CoverageRuleCreate(StrictModel):
    auto_approve_threshold: Money
    auto_approved_diagnoses: list[str]
    excluded_diagnoses: list[str]
    per_claim_cap: Money
    buffer_pct: Percent
    deductible: Money
    copay_pct: Percent
    reason_codes: list[str]
