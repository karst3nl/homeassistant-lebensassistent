"""Konten-/Kategorien-SQL; Commit und Audit gehören zur Serviceschicht."""

import sqlite3
from typing import Literal

Table = Literal["accounts", "categories"]


def _table(table: Table) -> str:
    if table not in ("accounts", "categories"):
        raise ValueError("Unknown catalog table")
    return table


def records(connection: sqlite3.Connection, table: Table) -> list[dict]:
    return [
        dict(row)
        for row in connection.execute(
            f"SELECT * FROM {_table(table)} ORDER BY sort_order, id"
        )
    ]


def record(connection: sqlite3.Connection, table: Table, entity_id: int) -> dict | None:
    row = connection.execute(
        f"SELECT * FROM {_table(table)} WHERE id = ?", (entity_id,)
    ).fetchone()
    return dict(row) if row is not None else None


def insert_account(connection: sqlite3.Connection, values: dict, now: str) -> dict:
    row = connection.execute(
        """INSERT INTO accounts
           (name, account_type, opening_balance_cents, opening_date, notes,
            created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING *""",
        (
            values["name"],
            values["account_type"],
            values["opening_balance_cents"],
            values["opening_date"],
            values["notes"],
            now,
            now,
        ),
    ).fetchone()
    return dict(row)


def insert_category(connection: sqlite3.Connection, values: dict, now: str) -> dict:
    row = connection.execute(
        """INSERT INTO categories (name, kind, parent_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?) RETURNING *""",
        (values["name"], values["kind"], values["parent_id"], now, now),
    ).fetchone()
    return dict(row)


def set_active(
    connection: sqlite3.Connection, table: Table, entity_id: int, active: bool, now: str
) -> dict:
    row = connection.execute(
        f"UPDATE {_table(table)} SET is_active = ?, updated_at = ? "
        "WHERE id = ? RETURNING *",
        (int(active), now, entity_id),
    ).fetchone()
    return dict(row)


def has_active_children(connection: sqlite3.Connection, parent_id: int) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM categories WHERE parent_id = ? AND is_active = 1 LIMIT 1",
            (parent_id,),
        ).fetchone()
        is not None
    )
