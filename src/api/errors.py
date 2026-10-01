"""Map typed domain errors to the `{"error": {"code", "message"}}` envelope (app_spec §7)."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.domain.exceptions import MediCardError

logger = logging.getLogger("medicard.api")


def envelope(status: int, code: str, message: str, details: object | None = None) -> JSONResponse:
    body: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status, content={"error": body})


async def _domain_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, MediCardError)
    if exc.status_hint >= 500:
        logger.error("domain.error", extra={"code": exc.code})
    return envelope(exc.status_hint, exc.code, exc.message, exc.details)


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Echo field locations and messages only - never the submitted values (may contain PHI).
    details = [{"loc": list(e.get("loc", ())), "msg": e.get("msg", "")} for e in exc.errors()]
    return envelope(422, "VALIDATION_ERROR", "request validation failed", details)


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
    return envelope(exc.status_code, code, str(exc.detail))


async def _unexpected(_: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled.error", extra={"error_type": type(exc).__name__})
    return envelope(500, "INTERNAL_ERROR", "unexpected error")


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(MediCardError, _domain_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unexpected)
