"""NFR-08 rule: insurer override requires the ADMIN role check AND writes an audit record atomically."""

import sqlite3

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from src.config.settings import Settings
from src.domain.enums import Role
from src.main import create_app
from src.repository import audit_repo
from tests.api.helpers import submit_preauth
from tests.architecture.test_controllers_guarded import _flatten


def _override_route() -> APIRoute:
    app = create_app(settings=Settings(db_path=":memory:", secret="architecture-test-secret",
                                    seed_on_startup=False, frontend_dist=None))
    return next(r for r in _flatten(list(app.routes)) if r.path == "/api/admin/preauths/{preauth_id}/override")


@pytest.mark.nfr("NFR-08")
@pytest.mark.ac("AC-10")
def test_override_route_requires_exactly_admin() -> None:
    guards = [d.call for d in _override_route().dependant.dependencies if getattr(d.call, "__medicard_guard__", False)]
    assert len(guards) == 1
    roles = guards[0].__closure__[0].cell_contents  # type: ignore[index, union-attr]
    assert tuple(roles) == (Role.ADMIN,)


@pytest.mark.nfr("NFR-08")
@pytest.mark.ac("AC-10")
def test_failed_audit_write_rolls_back_the_override(  # type: ignore[no-untyped-def]
    client: TestClient, login, settings: Settings, monkeypatch
) -> None:
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="Z41.1", estimate="10000.00")

    def broken_insert(*_: object, **__: object) -> None:
        raise sqlite3.OperationalError("audit store unavailable")

    monkeypatch.setattr(audit_repo, "insert", broken_insert)
    lenient = TestClient(client.app, raise_server_exceptions=False)  # observe the 500 instead of raising
    resp = lenient.post(f"/api/admin/preauths/{pre['preauth_id']}/override",
                        json={"status": "APPROVED", "reason": "necessity"}, headers=login("admin.sam"))
    assert resp.status_code == 500
    conn = sqlite3.connect(settings.db_path)
    statuses = [row[0] for row in conn.execute(
        "SELECT status FROM preauth_decisions WHERE preauth_id = ? ORDER BY seq", (pre["preauth_id"],))]
    conn.close()
    assert statuses[-1] == "REJECTED", "override decision must not survive without its audit record"


@pytest.mark.nfr("NFR-02")
def test_audit_records_are_append_only(client: TestClient, login, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    pre = submit_preauth(client, login("cityhosp.desk"), diagnosis="Z41.1", estimate="10000.00")
    client.post(f"/api/admin/preauths/{pre['preauth_id']}/override", json={"status": "APPROVED", "reason": "ok"},
                headers=login("admin.sam"))
    conn = sqlite3.connect(settings.db_path)
    for sql in ("UPDATE audit_records SET reason = 'edited'", "DELETE FROM audit_records"):
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            conn.execute(sql)
    conn.close()
