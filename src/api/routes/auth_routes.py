"""Login and current-principal endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from src.api.deps import AnyUser, AppClock, AppSettings, DbConn
from src.api.schemas import LoginRequest
from src.service import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, conn: DbConn, settings: AppSettings, clock: AppClock) -> dict[str, object]:
    # public-endpoint: credentials are the input here
    user = auth_service.authenticate(conn, body.username.strip().lower(), body.password)
    token = auth_service.issue_token(
        user_id=user["id"], role=user["role"], secret=settings.secret, now=clock.now(),
        ttl_hours=settings.token_ttl_hours,
    )
    return {"token": token, "role": user["role"], "username": user["username"], "display_name": user["display_name"]}


@router.get("/me")
def me(principal: AnyUser) -> dict[str, object]:
    return {
        "username": principal.username,
        "role": principal.role.value,
        "display_name": principal.display_name,
        "hospital_code": principal.hospital_code,
        "customer_id": principal.customer_id,
    }
