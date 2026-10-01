"""AC-02 eligibility lookup (HOSPITAL only; hospital taken from the token, EL-R6)."""

from __future__ import annotations

from fastapi import APIRouter

from src.api.deps import AppClock, DbConn, HospitalUser
from src.api.schemas import EligibilityRequest
from src.service import eligibility_service

router = APIRouter(prefix="/api", tags=["eligibility"])


@router.post("/eligibility")
def check_eligibility(
    body: EligibilityRequest, conn: DbConn, clock: AppClock, principal: HospitalUser
) -> dict[str, object]:
    return eligibility_service.check(
        conn, principal, member_id=body.member_id, policy_number=body.policy_number, clock=clock
    )
