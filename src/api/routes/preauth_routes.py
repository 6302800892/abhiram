"""Pre-auth (hospital portal) and adjudicator workbench endpoints (AC-03, AC-04, AC-05)."""

from __future__ import annotations

from fastapi import APIRouter, status

from src.api.deps import AppClock, DbConn, HospitalUser, InsurerUser, PreAuthViewer, StaffUser
from src.api.schemas import DecisionCreate, PreAuthCreate, QueryResponse
from src.domain.enums import PreAuthStatus
from src.service import adjudication_service, preauth_service
from src.service.preauth_service import PreAuthRequest

router = APIRouter(prefix="/api", tags=["preauth"])


@router.post("/preauths", status_code=status.HTTP_201_CREATED)
def submit_preauth(body: PreAuthCreate, conn: DbConn, clock: AppClock, principal: HospitalUser) -> dict[str, object]:
    request = PreAuthRequest(
        member_id=body.member_id, policy_number=body.policy_number, diagnosis_code=body.diagnosis_code.upper(),
        estimated_cost=body.estimated_cost, expected_admission_date=body.expected_admission_date,
        clinical_notes=body.clinical_notes,
    )
    return preauth_service.submit(conn, principal, request, clock)


@router.get("/preauths")
def list_preauths(conn: DbConn, principal: PreAuthViewer) -> list[dict[str, object]]:
    return preauth_service.list_for(conn, principal)


@router.get("/preauths/{preauth_id}")
def get_preauth(preauth_id: int, conn: DbConn, principal: PreAuthViewer) -> dict[str, object]:
    preauth_service.load_visible(conn, principal, preauth_id)
    return preauth_service.view(conn, preauth_id)


@router.post("/preauths/{preauth_id}/query-response")
def answer_query(
    preauth_id: int, body: QueryResponse, conn: DbConn, clock: AppClock, principal: HospitalUser
) -> dict[str, object]:
    return preauth_service.answer_query(conn, principal, preauth_id, body.response_note, clock)


@router.post("/preauths/{preauth_id}/decisions")
def decide(
    preauth_id: int, body: DecisionCreate, conn: DbConn, clock: AppClock, principal: InsurerUser
) -> dict[str, object]:
    return adjudication_service.decide(
        conn, principal, preauth_id, status=PreAuthStatus(body.status), approved_amount=body.approved_amount,
        reason_codes=body.reason_codes, note=body.note, clock=clock,
    )


@router.get("/adjudication/queue")
def review_queue(conn: DbConn, clock: AppClock, principal: StaffUser) -> list[dict[str, object]]:
    return adjudication_service.queue(conn, clock)
