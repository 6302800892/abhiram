"""Case lifecycle, timeline and settlement endpoints (AC-06 .. AC-09)."""

from __future__ import annotations

from fastapi import APIRouter, status

from src.api.deps import AppClock, CaseCloser, CaseViewer, DbConn, HospitalUser, InsurerUser
from src.api.schemas import AdmitRequest, DischargeRequest, DisputeRequest, FinalBillCreate, ProcedureCreate
from src.service import case_service, settlement_service, timeline_service

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("")
def list_cases(conn: DbConn, principal: CaseViewer) -> list[dict[str, object]]:
    return case_service.list_cases(conn, principal)


@router.get("/{case_id}")
def get_case(case_id: int, conn: DbConn, principal: CaseViewer) -> dict[str, object]:
    case_service.load_visible(conn, principal, case_id)
    return case_service.detail(conn, case_id)


@router.get("/{case_id}/timeline")
def get_timeline(case_id: int, conn: DbConn, principal: CaseViewer) -> list[dict[str, object]]:
    case_service.load_visible(conn, principal, case_id)
    return timeline_service.timeline_view(conn, case_id)


@router.post("/{case_id}/admit")
def admit(
    case_id: int, body: AdmitRequest, conn: DbConn, clock: AppClock, principal: HospitalUser
) -> dict[str, object]:
    return case_service.admit(conn, principal, case_id, body.admitted_on, clock)


@router.post("/{case_id}/procedures", status_code=status.HTTP_201_CREATED)
def add_procedure(
    case_id: int, body: ProcedureCreate, conn: DbConn, clock: AppClock, principal: HospitalUser
) -> dict[str, object]:
    return case_service.add_procedure(conn, principal, case_id, body.procedure_code, body.description, clock)


@router.post("/{case_id}/final-bill", status_code=status.HTTP_201_CREATED)
def submit_final_bill(
    case_id: int, body: FinalBillCreate, conn: DbConn, clock: AppClock, principal: HospitalUser
) -> dict[str, object]:
    return case_service.submit_final_bill(conn, principal, case_id, body.amount, clock)


@router.post("/{case_id}/discharge")
def discharge(
    case_id: int, body: DischargeRequest, conn: DbConn, clock: AppClock, principal: HospitalUser
) -> dict[str, object]:
    return case_service.discharge(conn, principal, case_id, body.discharged_on, clock)


@router.post("/{case_id}/dispute")
def dispute(
    case_id: int, body: DisputeRequest, conn: DbConn, clock: AppClock, principal: InsurerUser
) -> dict[str, object]:
    return case_service.dispute(conn, principal, case_id, body.reason, clock)


@router.post("/{case_id}/close")
def close(case_id: int, conn: DbConn, clock: AppClock, principal: CaseCloser) -> dict[str, object]:
    return case_service.close(conn, principal, case_id, clock)


@router.post("/{case_id}/settle")
def settle(case_id: int, conn: DbConn, clock: AppClock, principal: InsurerUser) -> dict[str, object]:
    return settlement_service.settle(conn, principal, case_id, clock)


@router.get("/{case_id}/settlement")
def get_settlement(case_id: int, conn: DbConn, principal: CaseViewer) -> dict[str, object]:
    return settlement_service.get_settlement(conn, principal, case_id)
