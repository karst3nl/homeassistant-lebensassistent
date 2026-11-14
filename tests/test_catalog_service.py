"""Konten/Kategorien nur mit synthetischen Daten und isolierter Datenbank."""

import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from lebensassistent.database.audit import append_audit
from lebensassistent.database.connection import Database, transaction
from lebensassistent.database.migrations import MIGRATIONS, migrate
from lebensassistent.services.catalog import (
    AccountInput,
    CatalogError,
    CatalogService,
    CategoryInput,
)


@pytest.fixture
def service(tmp_path: Path) -> CatalogService:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database)
    return CatalogService(database)


def account(**overrides: object) -> AccountInput:
    return AccountInput.model_validate(
        {
            "name": "Synthetisches Girokonto",
            "account_type": "checking",
            "opening_balance_cents": -12345,
            "opening_date": "2026-01-15",
            **overrides,
        }
    )


def test_create_archive_and_reactivate_keep_opening_balance(
    service: CatalogService,
) -> None:
    created = service.create_account(account())
    assert created["opening_balance_cents"] == -12345
    archived = service.set_active("accounts", created["id"], False)
    assert archived["is_active"] == 0
    assert archived["opening_date"] == "2026-01-15"
    assert archived["opening_balance_cents"] == -12345
    restored = service.set_active("accounts", created["id"], True)
    assert restored["is_active"] == 1
    assert service.accounts()[0]["id"] == created["id"]
    with service.database.connect() as connection:
        events = connection.execute(
            "SELECT action FROM audit_log WHERE entity_type = 'accounts' ORDER BY id"
        ).fetchall()
    assert [row[0] for row in events] == ["create", "archive", "reactivate"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "  "},
        {"name": "s" * 101},
        {"account_type": "invalid"},
        {"opening_balance_cents": 1.5},
        {"opening_balance_cents": True},
        {"opening_balance_cents": 2**63},
        {"opening_date": "2026-02-30"},
        {"opening_date": "20260101"},
        {"opening_date": True},
        {"is_active": False},
    ],
)
def test_invalid_account_data_is_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        account(**overrides)


def test_status_change_is_idempotent_and_unknown_id_is_rejected(
    service: CatalogService,
) -> None:
    created = service.create_account(account())
    service.set_active("accounts", created["id"], True)
    with service.database.connect() as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM audit_log WHERE entity_type = 'accounts'"
            ).fetchone()[0]
            == 1
        )
    with pytest.raises(CatalogError):
        service.set_active("accounts", 999, False)


def test_category_parent_must_be_active_same_kind(service: CatalogService) -> None:
    parent = service.create_category(
        CategoryInput(name="Synthetische Einnahmen", kind="income")
    )
    with pytest.raises(CatalogError):
        service.create_category(
            CategoryInput(
                name="Synthetische Ausgabe", kind="expense", parent_id=parent["id"]
            )
        )
    child = service.create_category(
        CategoryInput(
            name="Synthetische Unterkategorie", kind="income", parent_id=parent["id"]
        )
    )
    with pytest.raises(CatalogError):
        service.set_active("categories", parent["id"], False)
    service.set_active("categories", child["id"], False)
    service.set_active("categories", parent["id"], False)
    with pytest.raises(CatalogError):
        service.set_active("categories", child["id"], True)
    assert len(service.categories()) == 2


@pytest.mark.parametrize(
    "values",
    [
        {"name": "", "kind": "expense"},
        {"name": "synthetic", "kind": "other"},
        {"name": "synthetic", "kind": "expense", "parent_id": 0},
        {"name": "synthetic", "kind": "expense", "parent_id": True},
    ],
)
def test_invalid_categories_are_rejected(values: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        CategoryInput.model_validate(values)


def test_audit_failure_rolls_back_new_account(service: CatalogService) -> None:
    with service.database.connect() as connection:
        connection.execute(
            "CREATE TRIGGER synthetic_audit_failure BEFORE INSERT ON audit_log "
            "WHEN NEW.entity_type = 'accounts' "
            "BEGIN SELECT RAISE(ABORT, 'synthetic audit failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="synthetic audit failure"):
        service.create_account(account())
    assert service.accounts() == []


def test_upgrade_from_v1_preserves_existing_audit(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database, MIGRATIONS[:1])
    with database.connect() as connection, transaction(connection):
        append_audit(connection, entity_type="synthetic", entity_id=1, action="test")
    # Preserve the historical v1 -> v2 upgrade regression.
    assert migrate(database, MIGRATIONS[:2]) == 2
    with database.connect() as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM audit_log WHERE entity_type = 'synthetic'"
            ).fetchone()[0]
            == 1
        )
        assert (
            connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[
                0
            ]
            == 2
        )
