"""Application factory and `medicard` console entry point (poetry run medicard)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from src.api.errors import install_error_handlers
from src.api.middleware import install_middleware
from src.api.routes import (
    admin_routes,
    auth_routes,
    case_routes,
    customer_routes,
    eligibility_routes,
    health_routes,
    override_routes,
    preauth_routes,
    report_routes,
)
from src.api.static import mount_frontend
from src.config.logging_config import configure_logging, uvicorn_log_config
from src.config.settings import Settings
from src.domain.clock import Clock, SystemClock
from src.repository.db import apply_migrations, connect
from src.service.seed_service import seed_if_empty

logger = logging.getLogger("medicard.startup")
MIN_SECRET_LENGTH = 16
ROUTERS = (
    health_routes, auth_routes, customer_routes, eligibility_routes, admin_routes, preauth_routes, case_routes,
    override_routes, report_routes,
)


def _bootstrap(settings: Settings, clock: Clock) -> None:
    """Apply append-only migrations (tamper check) and load seed data into an empty DB."""
    conn = connect(settings.db_path)
    try:
        applied = apply_migrations(conn, Path(settings.migrations_dir))
        seeded = settings.seed_on_startup and seed_if_empty(
            conn, settings.seed_file, clock=clock, iterations=settings.pbkdf2_iterations
        )
        logger.info("startup.ready", extra={"migrations_applied": len(applied), "seeded": bool(seeded)})
    finally:
        conn.close()


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    if len(settings.secret) < MIN_SECRET_LENGTH:
        raise ValueError(f"MEDICARD_SECRET must be at least {MIN_SECRET_LENGTH} characters (SEC-12)")
    clock = clock or SystemClock()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        _bootstrap(settings, clock)
        yield

    app = FastAPI(title="MediCard", version="1.0.0", lifespan=lifespan,
                  description="Health cashless hospitalization & settlement platform (BC-AINE-017)")
    app.state.settings = settings
    app.state.clock = clock
    install_error_handlers(app)
    install_middleware(app)
    for module in ROUTERS:
        app.include_router(module.router)
    mount_frontend(app, settings.frontend_dist)
    return app


def run() -> None:
    """Console entry point: start uvicorn with settings from MEDICARD_* env vars."""
    import uvicorn

    settings = Settings.from_env()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port,
                log_config=uvicorn_log_config(settings.log_level))


if __name__ == "__main__":
    run()
