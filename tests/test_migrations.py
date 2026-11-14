"""Fresh-DB und Upgrades mit ausschließlich synthetischen Zusatzmigrationen."""

import sqlite3
from pathlib import Path

import pytest

from lebensassistent.database.connection import Database
from lebensassistent.database.migrations import (
    MIGRATIONS as CURRENT_MIGRATIONS,
)
from lebensassistent.database.migrations import (
    Migration,
    MigrationError,
    migrate,
)

# Keep the original v1 harness isolated from later production migrations.
MIGRATIONS = CURRENT_MIGRATIONS[:1]

SYNTHETIC_V2 = Migration(
    2,
    "synthetic_test_table",
    ("CREATE TABLE synthetic_items (id INTEGER PRIMARY KEY, label TEXT NOT NULL)",),
)
SYNTHETIC_V3 = Migration(
    3, "synthetic_test_column", ("ALTER TABLE synthetic_items ADD COLUMN note TEXT",)
)


def test_fresh_database_and_repeated_start_are_idempotent(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    assert migrate(database, MIGRATIONS) == 1
    assert migrate(database, MIGRATIONS) == 1
    with database.connect() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
            == 1
        )
        assert connection.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 1
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert tables == {"schema_migrations", "audit_log"}


def test_upgrade_preserves_synthetic_rows_and_audit(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database, (*MIGRATIONS, SYNTHETIC_V2))
    with database.connect() as connection:
        connection.execute("INSERT INTO synthetic_items VALUES (1, 'synthetic label')")
    assert migrate(database, (*MIGRATIONS, SYNTHETIC_V2, SYNTHETIC_V3)) == 3
    with database.connect() as connection:
        row = connection.execute("SELECT label, note FROM synthetic_items").fetchone()
        assert tuple(row) == ("synthetic label", None)
        assert connection.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 3


def test_failed_upgrade_rolls_back_ddl_data_versions_and_audit(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database, MIGRATIONS)
    broken = Migration(
        3,
        "synthetic_broken_upgrade",
        (
            "INSERT INTO synthetic_items VALUES (1, 'synthetic row')",
            "INVALID SYNTHETIC SQL",
        ),
    )
    with pytest.raises(sqlite3.OperationalError):
        migrate(database, (*MIGRATIONS, SYNTHETIC_V2, broken))
    with database.connect() as connection:
        assert (
            connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[
                0
            ]
            == 1
        )
        assert connection.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 1
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name = 'synthetic_items'"
            ).fetchone()
            is None
        )
    assert migrate(database, (*MIGRATIONS, SYNTHETIC_V2)) == 2


def test_failed_initial_migration_leaves_no_partial_schema(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    broken = Migration(
        1,
        "synthetic_broken_initial",
        ("CREATE TABLE synthetic_partial (id INTEGER)", "INVALID SQL"),
    )
    with pytest.raises(sqlite3.OperationalError):
        migrate(database, (broken,))
    with database.connect() as connection:
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
            == []
        )


@pytest.mark.parametrize("versions", [(2,), (1, 1), (1, 3), (2, 1)])
def test_migration_registry_must_be_ordered_and_contiguous(
    tmp_path: Path, versions: tuple[int, ...]
) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    registry = tuple(Migration(version, "synthetic", ()) for version in versions)
    with pytest.raises(ValueError, match="contiguous"):
        migrate(database, registry)


def test_newer_database_is_rejected_without_deleting_data(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database, (*MIGRATIONS, SYNTHETIC_V2))
    with pytest.raises(MigrationError):
        migrate(database, MIGRATIONS)
    with database.connect() as connection:
        assert (
            connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[
                0
            ]
            == 2
        )


def test_changed_migration_checksum_is_rejected(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database, MIGRATIONS)
    changed = Migration(1, MIGRATIONS[0].name, (*MIGRATIONS[0].statements, "SELECT 1"))
    with pytest.raises(MigrationError, match="history"):
        migrate(database, (changed,))
