"""FastAPI dependencies: DB connection, clock, settings and the role guard (NFR-04 boundary)."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, Header, Request

from src.config.settings import Settings
from src.domain.clock import Clock
from src.domain.enums import Role
from src.domain.exceptions import AuthenticationError, AuthorizationError
from src.domain.principal import Principal
from src.repository.db import connect
from src.service import auth_service


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock


def get_conn(settings: Annotated[Settings, Depends(get_settings)]) -> Iterator[sqlite3.Connection]:
    """One connection per request; services own their transactions with `with conn:`."""
    conn = connect(settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


DbConn = Annotated[sqlite3.Connection, Depends(get_conn)]
AppClock = Annotated[Clock, Depends(get_clock)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def current_principal(
    conn: DbConn,
    settings: AppSettings,
    clock: AppClock,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    """Resolve the caller from `Authorization: Bearer <token>`; any authenticated role passes."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError("missing bearer token")
    claims = auth_service.verify_token(authorization[7:].strip(), secret=settings.secret, now=clock.now())
    return auth_service.load_principal(conn, claims)


current_principal.__medicard_guard__ = True  # type: ignore[attr-defined]


def require_roles(*roles: Role) -> Callable[..., Principal]:
    """Dependency factory: allow only the given roles (403 otherwise). Hospitals must be bound to a hospital."""

    def _guard(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
        if principal.role not in roles:
            raise AuthorizationError(f"requires one of {[r.value for r in roles]}")
        if principal.role is Role.HOSPITAL and principal.hospital_id is None:
            raise AuthorizationError("hospital user is not bound to a hospital")
        return principal

    _guard.__medicard_guard__ = True  # type: ignore[attr-defined]
    return _guard


AnyUser = Annotated[Principal, Depends(current_principal)]
CustomerUser = Annotated[Principal, Depends(require_roles(Role.CUSTOMER))]
HospitalUser = Annotated[Principal, Depends(require_roles(Role.HOSPITAL))]
InsurerUser = Annotated[Principal, Depends(require_roles(Role.INSURER))]
AdminUser = Annotated[Principal, Depends(require_roles(Role.ADMIN))]
StaffUser = Annotated[Principal, Depends(require_roles(Role.INSURER, Role.ADMIN))]
CaseViewer = Annotated[Principal, Depends(require_roles(Role.CUSTOMER, Role.HOSPITAL, Role.INSURER, Role.ADMIN))]
PreAuthViewer = Annotated[Principal, Depends(require_roles(Role.HOSPITAL, Role.INSURER, Role.ADMIN))]
CaseCloser = Annotated[Principal, Depends(require_roles(Role.INSURER, Role.ADMIN))]
