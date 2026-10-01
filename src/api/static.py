"""Serve the built React portal (frontend/dist) from the same origin as the API."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles


def mount_frontend(app: FastAPI, dist: str | None) -> None:
    """Mount /assets and an SPA fallback when a build exists; otherwise do nothing."""
    if not dist or not (Path(dist) / "index.html").is_file():
        return
    root = Path(dist).resolve()
    app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> Response:  # public-endpoint: static UI shell, no data
        if path.startswith("api/") or path == "api":
            return JSONResponse({"error": {"code": "NOT_FOUND", "message": "unknown API path"}}, status_code=404)
        candidate = (root / path).resolve()
        if path and candidate.is_file() and root in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(root / "index.html")
