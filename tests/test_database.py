"""SQLite-Dateien ausschließlich in isolierten temporären Verzeichnissen."""

import sqlite3
from pathlib import Path

import pytest

from lebensassistent.database.connection import Database, transaction


def test_every_connection_enables_wal_and_foreign_keys(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    for _ in range(2):
        with database.connect() as connection:
            assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
            assert connection.execute("PRAGMA synchronous").fetchone()[0] == 2
            assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")


def test_committed_changes_survive_a_new_connection(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    with database.connect() as connection, transaction(connection):
        connection.execute("CREATE TABLE synthetic_items (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO synthetic_items VALUES (1)")
    with database.connect() as connection:
        assert connection.execute("SELECT id FROM synthetic_items").fetchone()[0] == 1


def test_foreign_key_error_rolls_back_entire_transaction(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    with database.connect() as connection:
        connection.execute("CREATE TABLE synthetic_parent (id INTEGER PRIMARY KEY)")
        connection.execute(
            "CREATE TABLE synthetic_child "
            "(parent_id INTEGER REFERENCES synthetic_parent(id))"
        )
        with pytest.raises(sqlite3.IntegrityError), transaction(connection):
            connection.execute("INSERT INTO synthetic_parent VALUES (1)")
            connection.execute("INSERT INTO synthetic_child VALUES (999)")
        assert (
            connection.execute("SELECT COUNT(*) FROM synthetic_parent").fetchone()[0]
            == 0
        )


def test_nested_transaction_is_rejected_without_committing_outer_changes(
    tmp_path: Path,
) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    with database.connect() as connection:
        connection.execute("CREATE TABLE synthetic_items (id INTEGER PRIMARY KEY)")
        with pytest.raises(RuntimeError, match="active"), transaction(connection):
            connection.execute("INSERT INTO synthetic_items VALUES (1)")
            with transaction(connection):
                pass
        assert (
            connection.execute("SELECT COUNT(*) FROM synthetic_items").fetchone()[0]
            == 0
        )


def test_database_requires_explicit_absolute_path() -> None:
    with pytest.raises(ValueError, match="absolute"):
        Database(Path("synthetic.sqlite3"))
