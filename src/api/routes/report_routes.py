"""Operational reports (INSURER, ADMIN)."""

from __future__ import annotations

from fastapi import APIRouter

from src.api.deps import DbConn, StaffUser
from src.service import report_service

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/summary")
def summary(conn: DbConn, principal: StaffUser) -> dict[str, object]:
    return report_service.summary(conn)
