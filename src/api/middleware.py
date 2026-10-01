"""Correlation-id middleware and request logging (NFR-06)."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from src.config.logging_config import bind_case_id, bind_correlation_id

logger = logging.getLogger("medicard.http")
HEADER = "X-Correlation-ID"


def install_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def correlation(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        correlation_id = request.headers.get(HEADER) or uuid.uuid4().hex
        bind_correlation_id(correlation_id[:64])
        bind_case_id(None)
        started = time.perf_counter()
        response = await call_next(request)
        response.headers[HEADER] = correlation_id[:64]
        logger.info(
            "http.request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),  # money-float-ok
            },
        )
        return response
