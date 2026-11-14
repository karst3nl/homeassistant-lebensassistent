"""Audit und synthetische Änderungen müssen dieselbe Transaktion teilen."""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from lebensassistent.database.audit import append_audit
from lebensassistent.database.connection import Database, transaction
from lebensassistent.database.migrations import migrate


def test_audit_stores_json_utc_and_literal_sql_like_text(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database)
    snapshot = {"label": "synthetic ' ; DROP TABLE audit_log; --"}
    with database.connect() as connection, transaction(connection):
        audit_id = append_audit(
            connection,
            entity_type="synthetic",
            entity_id=1,
            action="create",
            after=snapshot,
        )
    with database.connect() as connection:
        row = connection.execute(
            "SELECT * FROM audit_log WHERE id = ?", (audit_id,)
        ).fetchone()
        assert row["before_json"] is None
        assert json.loads(row["after_json"]) == snapshot
        assert datetime.fromisoformat(row["occurred_at"]).utcoffset() == timedelta(0)


def test_audit_refuses_writes_outside_transaction(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database)
    with (
        database.connect() as connection,
        pytest.raises(RuntimeError, match="transaction"),
    ):
        append_audit(connection, entity_type="synthetic", entity_id=1, action="create")


def test_audit_rolls_back_with_synthetic_business_failure(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database)
    with database.connect() as connection:
        connection.execute("CREATE TABLE synthetic_items (id INTEGER PRIMARY KEY)")
        with pytest.raises(sqlite3.IntegrityError), transaction(connection):
            connection.execute("INSERT INTO synthetic_items VALUES (1)")
            append_audit(
                connection, entity_type="synthetic", entity_id=1, action="create"
            )
            connection.execute("INSERT INTO synthetic_items VALUES (1)")
        assert (
            connection.execute("SELECT COUNT(*) FROM synthetic_items").fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM audit_log WHERE entity_type = 'synthetic'"
            ).fetchone()[0]
            == 0
        )


@pytest.mark.parametrize(
    "statement", ["DELETE FROM audit_log", "UPDATE audit_log SET action = 'synthetic'"]
)
def test_audit_entries_cannot_be_changed(tmp_path: Path, statement: str) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database)
    with (
        database.connect() as connection,
        pytest.raises(sqlite3.IntegrityError, match="immutable"),
    ):
        connection.execute(statement)


@pytest.mark.parametrize("invalid", [float("nan"), float("inf")])
def test_audit_rejects_nonfinite_json_without_partial_write(
    tmp_path: Path, invalid: float
) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database)
    with database.connect() as connection:
        with pytest.raises(ValueError), transaction(connection):
            append_audit(
                connection,
                entity_type="synthetic",
                entity_id=1,
                action="create",
                after={"invalid": invalid},
            )
        assert connection.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 1
