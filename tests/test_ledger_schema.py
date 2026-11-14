"""Schema-3-Constraints mit ausschließlich synthetischen SQL-Daten."""

import sqlite3
from pathlib import Path

import pytest

from lebensassistent.database.connection import Database, transaction
from lebensassistent.database.migrations import MIGRATIONS, migrate
from lebensassistent.services.catalog import AccountInput, CatalogService, CategoryInput


@pytest.fixture
def database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database)
    catalog = CatalogService(database)
    catalog.create_account(
        AccountInput(
            name="Synthetisches Konto",
            account_type="checking",
            opening_balance_cents=10000,
            opening_date="2026-01-01",
        )
    )
    catalog.create_category(CategoryInput(name="Synthetisch", kind="expense"))
    return database


def test_schema_three_is_append_only_to_migration_history(database: Database) -> None:
    assert len(MIGRATIONS) == 3
    with database.connect() as connection:
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"transactions", "transaction_splits"} <= names
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("amount_cents", 0),
        ("amount_cents", -1),
        ("amount_cents", 1.5),
        ("booked_date", "2026-02-30"),
        ("booked_date", "0000-01-01"),
        ("kind", "transfer_out"),
        ("account_id", 999999),
        ("submission_id", "invalid"),
    ],
)
def test_invalid_transaction_cannot_enter_database(
    database: Database, column: str, value: object
) -> None:
    data = {
        "account_id": 1,
        "kind": "expense",
        "amount_cents": 123,
        "booked_date": "2026-01-15",
        "submission_id": "a" * 32,
        "created_at": "2026-01-15T12:00:00+00:00",
        "updated_at": "2026-01-15T12:00:00+00:00",
    }
    data[column] = value
    with database.connect() as connection:
        with pytest.raises(sqlite3.IntegrityError), transaction(connection):
            connection.execute(
                "INSERT INTO transactions "
                "(account_id, kind, amount_cents, booked_date, "
                "submission_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                tuple(data.values()),
            )
        assert (
            connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
        )


def test_split_foreign_keys_and_positive_amount(database: Database) -> None:
    with database.connect() as connection, transaction(connection):
        connection.execute(
            "INSERT INTO transactions (account_id, kind, amount_cents, booked_date, "
            "submission_id, created_at, updated_at) VALUES "
            "(1, 'expense', 123, '2026-01-15', ?, 'synthetic', 'synthetic')",
            ("a" * 32,),
        )
        for transaction_id, category_id, amount in (
            (999, 1, 123),
            (1, 999, 123),
            (1, 1, 0),
        ):
            with pytest.raises(sqlite3.IntegrityError):
                connection.execute(
                    "INSERT INTO transaction_splits "
                    "(transaction_id, category_id, amount_cents, created_at) "
                    "VALUES (?, ?, ?, 'synthetic')",
                    (transaction_id, category_id, amount),
                )
