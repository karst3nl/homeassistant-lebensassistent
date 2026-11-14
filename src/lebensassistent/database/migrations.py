"""Lückenlose, geprüfte Migrationen in einer gemeinsamen SQLite-Transaktion."""

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from lebensassistent.database.audit import append_audit
from lebensassistent.database.connection import Database, transaction


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]

    @property
    def checksum(self) -> str:
        contents = json.dumps(
            (self.version, self.name, self.statements), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(contents).hexdigest()


MIGRATIONS = (
    Migration(
        1,
        "audit_foundation",
        (
            """CREATE TABLE audit_log (
                id INTEGER PRIMARY KEY,
                entity_type TEXT NOT NULL CHECK(length(trim(entity_type)) > 0),
                entity_id INTEGER NOT NULL CHECK(entity_id > 0),
                action TEXT NOT NULL CHECK(length(trim(action)) > 0),
                before_json TEXT CHECK(before_json IS NULL OR json_valid(before_json)),
                after_json TEXT CHECK(after_json IS NULL OR json_valid(after_json)),
                reason TEXT,
                occurred_at TEXT NOT NULL
            ) STRICT""",
            "CREATE INDEX audit_entity ON audit_log (entity_type, entity_id, id)",
            """CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_log
               BEGIN SELECT RAISE(ABORT, 'Audit entries are immutable'); END""",
            """CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_log
               BEGIN SELECT RAISE(ABORT, 'Audit entries are immutable'); END""",
        ),
    ),
)


class MigrationError(RuntimeError):
    """Die vorhandene Historie passt nicht zu dieser Anwendungsversion."""


def migrate(database: Database, migrations: tuple[Migration, ...] = MIGRATIONS) -> int:
    versions = tuple(item.version for item in migrations)
    if versions != tuple(range(1, len(migrations) + 1)):
        raise ValueError("Migration versions must be contiguous and ordered from 1")

    with database.connect() as connection, transaction(connection):
        connection.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY CHECK(version > 0),
                name TEXT NOT NULL,
                checksum_sha256 TEXT NOT NULL CHECK(length(checksum_sha256) = 64),
                applied_at TEXT NOT NULL
            ) STRICT"""
        )
        history = connection.execute(
            "SELECT version, name, checksum_sha256 "
            "FROM schema_migrations ORDER BY version"
        ).fetchall()
        for expected, row in enumerate(history, start=1):
            if (
                expected > len(migrations)
                or row["version"] != expected
                or row["name"] != migrations[expected - 1].name
                or row["checksum_sha256"] != migrations[expected - 1].checksum
            ):
                raise MigrationError("Unsupported or modified migration history")

        for migration in migrations[len(history) :]:
            for statement in migration.statements:
                connection.execute(statement)
            connection.execute(
                """INSERT INTO schema_migrations
                   (version, name, checksum_sha256, applied_at) VALUES (?, ?, ?, ?)""",
                (
                    migration.version,
                    migration.name,
                    migration.checksum,
                    datetime.now(UTC).isoformat(timespec="microseconds"),
                ),
            )
            append_audit(
                connection,
                entity_type="schema_migration",
                entity_id=migration.version,
                action="apply",
                after={"version": migration.version, "name": migration.name},
            )
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise sqlite3.IntegrityError("Foreign key check failed")
    return len(migrations)
