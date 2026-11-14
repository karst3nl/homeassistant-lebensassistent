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
    Migration(
        2,
        "accounts_and_categories",
        (
            """CREATE TABLE accounts (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100),
                account_type TEXT NOT NULL
                    CHECK(account_type IN
                        ('checking', 'savings', 'cash', 'credit_card')),
                role TEXT NOT NULL DEFAULT 'general'
                    CHECK(role IN ('general', 'fixed_costs', 'savings')),
                opening_balance_cents INTEGER NOT NULL,
                opening_date TEXT NOT NULL CHECK(
                    opening_date BETWEEN '0001-01-01' AND '9999-12-31'
                    AND opening_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                    AND COALESCE(date(opening_date, '+0 days') = opening_date, 0)),
                is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
                include_in_liquidity INTEGER NOT NULL DEFAULT 1
                    CHECK(include_in_liquidity IN (0, 1)),
                sort_order INTEGER NOT NULL DEFAULT 0 CHECK(sort_order >= 0),
                notes TEXT CHECK(notes IS NULL OR length(notes) <= 2000),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            ) STRICT""",
            """CREATE TABLE categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 100),
                parent_id INTEGER CHECK(parent_id IS NULL OR parent_id != id),
                kind TEXT NOT NULL CHECK(kind IN ('income', 'expense')),
                is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
                sort_order INTEGER NOT NULL DEFAULT 0 CHECK(sort_order >= 0),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(id, kind),
                FOREIGN KEY(parent_id, kind) REFERENCES categories(id, kind)
                    ON DELETE RESTRICT
            ) STRICT""",
            "CREATE INDEX category_parent ON categories(parent_id)",
        ),
    ),
    Migration(
        3,
        "income_and_expense_postings",
        (
            """CREATE TABLE transactions (
                id INTEGER PRIMARY KEY,
                account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
                kind TEXT NOT NULL CHECK(kind IN ('income', 'expense')),
                amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                booked_date TEXT NOT NULL CHECK(
                    booked_date BETWEEN '0001-01-01' AND '9999-12-31'
                    AND booked_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
                    AND COALESCE(date(booked_date, '+0 days') = booked_date, 0)),
                description TEXT
                    CHECK(description IS NULL OR length(description) <= 2000),
                status TEXT NOT NULL DEFAULT 'posted'
                    CHECK(status IN ('posted', 'voided')),
                origin TEXT NOT NULL DEFAULT 'manual' CHECK(origin = 'manual'),
                void_reason TEXT,
                submission_id TEXT NOT NULL UNIQUE CHECK(
                    length(submission_id) = 32
                    AND submission_id NOT GLOB '*[^0-9a-f]*'),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            ) STRICT""",
            """CREATE TABLE transaction_splits (
                id INTEGER PRIMARY KEY,
                transaction_id INTEGER NOT NULL
                    REFERENCES transactions(id) ON DELETE RESTRICT,
                category_id INTEGER NOT NULL
                    REFERENCES categories(id) ON DELETE RESTRICT,
                amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                memo TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0 CHECK(sort_order >= 0),
                created_at TEXT NOT NULL,
                UNIQUE(transaction_id, sort_order)
            ) STRICT""",
            "CREATE INDEX transaction_account_date "
            "ON transactions(account_id, booked_date, id)",
            "CREATE INDEX split_category ON transaction_splits(category_id)",
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
