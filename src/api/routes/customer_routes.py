"""AC-01 customer endpoints."""

from __future__ import annotations

from fastapi import APIRouter, status

from src.api.deps import AppClock, AppSettings, CustomerUser, DbConn
from src.api.schemas import LinkPolicyRequest, RegisterRequest
from src.service import customer_service, timeline_service

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, conn: DbConn, clock: AppClock, settings: AppSettings) -> dict[str, object]:
    # public-endpoint: self-registration (EL-R1)
    customer_id = customer_service.register(
        conn, username=body.username, password=body.password, full_name=body.full_name, clock=clock,
        iterations=settings.pbkdf2_iterations,
    )
    return {"customer_id": customer_id, "username": body.username.lower()}


@router.post("/me/policies", status_code=status.HTTP_201_CREATED)
def link_policy(body: LinkPolicyRequest, conn: DbConn, principal: CustomerUser) -> dict[str, object]:
    return customer_service.link_policy(
        conn, principal, policy_number=body.policy_number, member_id=body.member_id,
        date_of_birth=body.date_of_birth.isoformat(),
    )


@router.get("/me/coverage")
def coverage(conn: DbConn, principal: CustomerUser) -> dict[str, object]:
    return customer_service.coverage(conn, principal)


@router.get("/me/notifications")
def notifications(conn: DbConn, principal: CustomerUser) -> list[dict[str, object]]:
    """AC-09: stub notifications for every state transition on the customer's cases."""
    if principal.customer_id is None:
        return []
    return timeline_service.notifications_view(conn, principal.customer_id)
