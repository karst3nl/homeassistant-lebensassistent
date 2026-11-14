"""Append-only Audit-Einträge innerhalb der Transaktion des Aufrufers."""

import json
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime


def append_audit(
    connection: sqlite3.Connection,
    *,
    entity_type: str,
    entity_id: int,
    action: str,
    before: Mapping[str, object] | None = None,
    after: Mapping[str, object] | None = None,
    reason: str | None = None,
) -> int:
    if not connection.in_transaction:
        raise RuntimeError("Audit writes require an active transaction")
    if not entity_type.strip() or not action.strip():
        raise ValueError("Audit entity and action must not be empty")
    if type(entity_id) is not int or entity_id <= 0:
        raise ValueError("Audit entity ID must be a positive integer")

    def snapshot(value: Mapping[str, object] | None) -> str | None:
        return (
            json.dumps(dict(value), ensure_ascii=False, sort_keys=True, allow_nan=False)
            if value is not None
            else None
        )

    cursor = connection.execute(
        """INSERT INTO audit_log
           (entity_type, entity_id, action, before_json, after_json,
            reason, occurred_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            entity_type,
            entity_id,
            action,
            snapshot(before),
            snapshot(after),
            reason,
            datetime.now(UTC).isoformat(timespec="microseconds"),
        ),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid
