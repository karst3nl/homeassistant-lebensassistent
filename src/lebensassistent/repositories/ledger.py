"""Parametrisiertes SQL für Normalbuchungen; keine gespeicherten Salden."""

import sqlite3
from datetime import date


def submitted(connection: sqlite3.Connection, submission_id: str) -> dict | None:
    row = connection.execute(
        "SELECT * FROM transactions WHERE submission_id = ?", (submission_id,)
    ).fetchone()
    if row is None:
        return None
    return {
        **dict(row),
        "splits": [
            dict(split)
            for split in connection.execute(
                "SELECT * FROM transaction_splits "
                "WHERE transaction_id = ? ORDER BY sort_order",
                (row["id"],),
            )
        ],
    }


def insert(connection: sqlite3.Connection, data: dict, now: str) -> dict:
    row = connection.execute(
        """INSERT INTO transactions
           (account_id, kind, amount_cents, booked_date, description, submission_id,
            created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING *""",
        (
            data["account_id"],
            data["kind"],
            data["amount_cents"],
            data["booked_date"],
            data["description"],
            data["submission_id"],
            now,
            now,
        ),
    ).fetchone()
    split = connection.execute(
        """INSERT INTO transaction_splits
           (transaction_id, category_id, amount_cents, created_at)
           VALUES (?, ?, ?, ?) RETURNING *""",
        (row["id"], data["category_id"], data["amount_cents"], now),
    ).fetchone()
    return {**dict(row), "splits": [dict(split)]}


def records(
    connection: sqlite3.Connection, account_id: int | None, limit: int
) -> list[dict]:
    return [
        dict(row)
        for row in connection.execute(
            """SELECT t.*, a.name AS account_name, c.name AS category_name,
                      s.category_id
               FROM transactions t
               JOIN accounts a ON a.id = t.account_id
               JOIN transaction_splits s ON s.transaction_id = t.id AND s.sort_order = 0
               JOIN categories c ON c.id = s.category_id
               WHERE (? IS NULL OR t.account_id = ?)
               ORDER BY t.booked_date DESC, t.id DESC LIMIT ?""",
            (account_id, account_id, limit),
        )
    ]


def balances(connection: sqlite3.Connection, on: date) -> dict[int, int | None]:
    # One SQL statement provides a consistent snapshot. Sum in Python integers:
    # SQLite SUM can overflow even when each individual stored amount is valid.
    result: dict[int, int | None] = {}
    for row in connection.execute(
        """SELECT a.id, a.opening_date, a.opening_balance_cents,
                  t.kind, t.amount_cents
           FROM accounts a LEFT JOIN transactions t ON t.account_id = a.id
               AND t.status = 'posted' AND t.booked_date <= ?
               AND t.booked_date >= a.opening_date
           ORDER BY a.id""",
        (on.isoformat(),),
    ):
        key = row["id"]
        if key not in result:
            result[key] = (
                row["opening_balance_cents"]
                if row["opening_date"] <= on.isoformat()
                else None
            )
        if result[key] is not None and row["amount_cents"] is not None:
            direction = 1 if row["kind"] == "income" else -1
            result[key] += direction * row["amount_cents"]
    return result
