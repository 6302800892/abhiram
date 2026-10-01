"""AC-10 audited override and the audit log (ADMIN only)."""

from __future__ import annotations

from fastapi import APIRouter

from src.api.deps import AdminUser, AppClock, DbConn
from src.api.schemas import OverrideRequest
from src.domain.enums import PreAuthStatus
from src.service import override_service

router = APIRouter(prefix="/api/admin", tags=["override"])


@router.post("/preauths/{preauth_id}/override")
def override_preauth(
    preauth_id: int, body: OverrideRequest, conn: DbConn, clock: AppClock, principal: AdminUser
) -> dict[str, object]:
    return override_service.override(
        conn, principal, preauth_id, target=PreAuthStatus(body.status), approved_amount=body.approved_amount,
        reason=body.reason, clock=clock,
    )


@router.get("/audit")
def audit_log(conn: DbConn, principal: AdminUser) -> list[dict[str, object]]:
    return override_service.audit_log(conn)
