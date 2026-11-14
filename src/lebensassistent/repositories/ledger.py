"""Parametrisiertes Buchungs-/Aufteilungs-SQL; keine gespeicherten Salden."""

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
    splits = []
    for index, part in enumerate(data["splits"]):
        split = connection.execute(
            """INSERT INTO transaction_splits
               (transaction_id, category_id, amount_cents, memo, sort_order, created_at)
               VALUES (?, ?, ?, ?, ?, ?) RETURNING *""",
            (
                row["id"],
                part["category_id"],
                part["amount_cents"],
                part["memo"],
                index,
                now,
            ),
        ).fetchone()
        splits.append(dict(split))
    return {**dict(row), "splits": splits}


def records(
    connection: sqlite3.Connection, account_id: int | None, limit: int
) -> list[dict]:
    parents: dict[int, dict] = {}
    for row in connection.execute(
        """WITH recent AS (
               SELECT * FROM transactions WHERE (? IS NULL OR account_id = ?)
               ORDER BY booked_date DESC, id DESC LIMIT ?
           )
           SELECT t.*, a.name AS account_name, s.id AS split_id,
                  s.category_id AS split_category_id, c.name AS split_category_name,
                  s.amount_cents AS split_amount_cents, s.memo AS split_memo,
                  s.sort_order AS split_sort_order, s.created_at AS split_created_at
           FROM recent t JOIN accounts a ON a.id = t.account_id
           JOIN transaction_splits s ON s.transaction_id = t.id
           JOIN categories c ON c.id = s.category_id
           ORDER BY t.booked_date DESC, t.id DESC, s.sort_order""",
        (account_id, account_id, limit),
    ):
        data = dict(row)
        part = {
            key: data.pop(f"split_{key}")
            for key in (
                "id",
                "category_id",
                "category_name",
                "amount_cents",
                "memo",
                "sort_order",
                "created_at",
            )
        }
        part["transaction_id"] = data["id"]
        if data["id"] not in parents:
            parents[data["id"]] = {**data, "splits": []}
        parents[data["id"]]["splits"].append(part)
    for record in parents.values():
        single = len(record["splits"]) == 1
        record["category_id"] = record["splits"][0]["category_id"] if single else None
        record["category_name"] = (
            record["splits"][0]["category_name"] if single else "Aufgeteilte Buchung"
        )
    return list(parents.values())


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
