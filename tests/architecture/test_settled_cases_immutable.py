"""NFR-08 rule: a SETTLED case cannot be mutated — by any service operation or by direct SQL."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.config.settings import Settings
from src.domain.exceptions import ConflictError
from src.domain.principal import Principal
from src.repository.db import connect
from src.service import auth_service, case_service, settlement_service
from tests.api.lifecycle import settled_case


def _principal(conn: sqlite3.Connection, username: str) -> Principal:
    user = conn.execute("SELECT id, role FROM users WHERE username = ?", (username,)).fetchone()
    return auth_service.load_principal(conn, auth_service.TokenClaims(user["id"], user["role"], 2**31))


@pytest.mark.nfr("NFR-08")
def test_every_mutating_case_operation_rejects_a_settled_case(  # type: ignore[no-untyped-def]
    client: TestClient, login, settings: Settings, clock
) -> None:
    case_id = settled_case(client, login)
    conn = connect(settings.db_path)
    hospital, insurer = _principal(conn, "cityhosp.desk"), _principal(conn, "adjudicator.priya")
    operations = {
        "add_procedure": lambda: case_service.add_procedure(conn, hospital, case_id, "GEN-ICU", "ICU", clock),
        "submit_final_bill": lambda: case_service.submit_final_bill(conn, hospital, case_id, __import__(
            "decimal").Decimal("1.00"), clock),
        "admit": lambda: case_service.admit(conn, hospital, case_id, clock.today(), clock),
        "discharge": lambda: case_service.discharge(conn, hospital, case_id, clock.today(), clock),
        "dispute": lambda: case_service.dispute(conn, insurer, case_id, "late", clock),
        "settle": lambda: settlement_service.settle(conn, insurer, case_id, clock),
    }
    for name, operation in operations.items():
        with pytest.raises(ConflictError):
            operation()
        assert conn.execute("SELECT status FROM claim_cases WHERE id = ?", (case_id,)).fetchone()[0] == "SETTLED", name
    conn.close()


@pytest.mark.nfr("NFR-08")
def test_settlement_rows_cannot_be_updated_or_deleted(client: TestClient, login, settings: Settings) -> None:  # type: ignore[no-untyped-def]
    settled_case(client, login)
    conn = connect(settings.db_path)
    for sql in ("UPDATE settlements SET settlement_amount = '999999.00'", "DELETE FROM settlements",
                "UPDATE final_bills SET amount = '1.00'"):
        with pytest.raises(sqlite3.DatabaseError, match="append-only"):
            conn.execute(sql)
    conn.close()
