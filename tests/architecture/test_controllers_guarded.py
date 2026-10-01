"""NFR-04 structural rule: every /api route sits behind a role guard except the public allowlist."""

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from src.config.settings import Settings
from src.main import create_app

PUBLIC = {("POST", "/api/auth/login"), ("POST", "/api/customers/register")}


def _guarded(dependant: Dependant) -> bool:
    for dep in dependant.dependencies:
        if getattr(dep.call, "__medicard_guard__", False) or _guarded(dep):
            return True
    return False


def _flatten(routes: list[object]) -> list[APIRoute]:
    """Walk included routers too (FastAPI >= 0.140 keeps them nested instead of copying routes)."""
    found: list[APIRoute] = []
    for route in routes:
        if isinstance(route, APIRoute):
            found.append(route)
        elif hasattr(route, "original_router"):
            found.extend(_flatten(list(route.original_router.routes)))
    return found


def _api_routes() -> list[APIRoute]:
    app = create_app(settings=Settings(db_path=":memory:", secret="architecture-test-secret",
                                    seed_on_startup=False, frontend_dist=None))
    return [r for r in _flatten(list(app.routes)) if r.path.startswith("/api")]


def test_every_api_route_is_guarded_or_explicitly_public() -> None:
    unguarded = []
    for route in _api_routes():
        for method in route.methods:
            if (method, route.path) not in PUBLIC and not _guarded(route.dependant):
                unguarded.append(f"{method} {route.path}")
    assert unguarded == []


def test_public_allowlist_is_minimal() -> None:
    paths = {(m, r.path) for r in _api_routes() for m in r.methods}
    assert PUBLIC <= paths
    assert len(PUBLIC) == 2
