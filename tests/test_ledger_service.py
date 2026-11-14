"""Atomare Normalbuchungen und Salden, ausschließlich synthetische Daten."""

import json
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from threading import Barrier
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from lebensassistent.database.connection import Database
from lebensassistent.database.migrations import MIGRATIONS, migrate
from lebensassistent.services.catalog import AccountInput, CatalogService, CategoryInput
from lebensassistent.services.ledger import LedgerError, LedgerService, PostingInput
from lebensassistent.services.values import MAX_CENTS, MIN_CENTS


def create_account(catalog: CatalogService, **overrides: object) -> dict:
    return catalog.create_account(
        AccountInput.model_validate(
            {
                "name": "Synthetisches Buchungskonto",
                "account_type": "checking",
                "opening_balance_cents": 10000,
                "opening_date": "2026-01-15",
                **overrides,
            }
        )
    )


@pytest.fixture
def ledger(tmp_path: Path) -> LedgerService:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database)
    catalog = CatalogService(database)
    create_account(catalog)
    catalog.create_category(CategoryInput(name="Synthetische Einnahme", kind="income"))
    catalog.create_category(CategoryInput(name="Synthetische Ausgabe", kind="expense"))
    return LedgerService(database)


def posting(**overrides: object) -> PostingInput:
    return PostingInput.model_validate(
        {
            "account_id": 1,
            "category_id": 1,
            "kind": "income",
            "amount_cents": 1001,
            "booked_date": "2026-01-16",
            "description": "Synthetische Testbuchung",
            "submission_id": uuid.uuid4().hex,
            **overrides,
        }
    )


def counts(ledger: LedgerService) -> tuple[int, int, int]:
    with ledger.database.connect() as connection:
        return (
            connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0],
            connection.execute("SELECT COUNT(*) FROM transaction_splits").fetchone()[0],
            connection.execute(
                "SELECT COUNT(*) FROM audit_log WHERE entity_type='transactions'"
            ).fetchone()[0],
        )


def test_income_and_expense_have_one_allocation_and_atomic_audit(
    ledger: LedgerService,
) -> None:
    income = ledger.post(posting())
    expense = ledger.post(
        posting(
            kind="expense", category_id=2, amount_cents=234, booked_date="2026-01-17"
        )
    )
    assert income["kind"] == "income"
    assert expense["amount_cents"] == 234
    assert counts(ledger) == (2, 2, 2)
    assert ledger.balance(1, date(2026, 1, 18)) == 10767
    with ledger.database.connect() as connection:
        rows = connection.execute(
            "SELECT transaction_id, category_id, amount_cents "
            "FROM transaction_splits ORDER BY transaction_id"
        ).fetchall()
        assert [tuple(row) for row in rows] == [
            (income["id"], 1, 1001),
            (expense["id"], 2, 234),
        ]
        audit = connection.execute(
            "SELECT action, before_json, after_json FROM audit_log "
            "WHERE entity_type='transactions' AND entity_id=?",
            (expense["id"],),
        ).fetchone()
        assert audit["action"] == "create"
        assert audit["before_json"] is None
        after = json.loads(audit["after_json"])
        assert after["id"] == expense["id"]
        assert after["amount_cents"] == 234
        assert len(after["splits"]) == 1
        assert after["splits"][0]["category_id"] == 2
        assert after["splits"][0]["amount_cents"] == 234


def test_balance_uses_opening_date_and_posted_entries_up_to_asof(
    ledger: LedgerService,
) -> None:
    ledger.post(posting())
    ledger.post(
        posting(
            kind="expense", category_id=2, amount_cents=234, booked_date="2026-01-17"
        )
    )
    future = ledger.post(posting(amount_cents=500, booked_date="2030-01-01"))
    voided = ledger.post(posting(amount_cents=700, booked_date="2026-01-16"))
    with ledger.database.connect() as connection:
        connection.execute(
            "UPDATE transactions SET status='voided', void_reason='synthetic fixture' "
            "WHERE id=?",
            (voided["id"],),
        )
    assert ledger.balance(1, date(2026, 1, 14)) is None
    assert ledger.balance(1, date(2026, 1, 15)) == 10000
    assert ledger.balance(1, date(2026, 1, 16)) == 11001
    assert ledger.balance(1, date(2026, 1, 17)) == 10767
    assert ledger.balance(1, date(2030, 1, 1)) == 11267
    assert future["booked_date"] == "2030-01-01"
    assert ledger.balances(date(2026, 1, 18)) == {1: 10767}


def test_entry_on_opening_date_is_included(ledger: LedgerService) -> None:
    ledger.post(posting(booked_date="2026-01-15", amount_cents=1))
    assert ledger.balance(1, date(2026, 1, 15)) == 10001


def test_archived_account_and_category_remain_in_history(ledger: LedgerService) -> None:
    created = ledger.post(posting())
    catalog = CatalogService(ledger.database)
    catalog.set_active("accounts", 1, False)
    catalog.set_active("categories", 1, False)
    assert ledger.balance(1, date(2026, 1, 18)) == 11001
    assert ledger.balances(date(2026, 1, 18)) == {1: 11001}
    assert [row["id"] for row in ledger.transactions(account_id=1)] == [created["id"]]


def test_balances_are_exact_beyond_sqlite_integer_sum_range(
    ledger: LedgerService,
) -> None:
    catalog = CatalogService(ledger.database)
    positive = create_account(catalog, opening_balance_cents=MAX_CENTS)
    negative = create_account(catalog, opening_balance_cents=MIN_CENTS)
    for _ in range(2):
        ledger.post(posting(account_id=positive["id"], amount_cents=MAX_CENTS))
        ledger.post(
            posting(
                account_id=negative["id"],
                kind="expense",
                category_id=2,
                amount_cents=MAX_CENTS,
            )
        )
    balances = ledger.balances(date(2026, 1, 18))
    assert balances[positive["id"]] == MAX_CENTS * 3
    assert balances[negative["id"]] == MIN_CENTS - MAX_CENTS * 2
    assert type(balances[positive["id"]]) is int
    assert type(balances[negative["id"]]) is int


def test_account_filter_limit_and_dated_order(ledger: LedgerService) -> None:
    second = create_account(CatalogService(ledger.database))
    first = ledger.post(posting(booked_date="2026-01-16"))
    latest = ledger.post(posting(booked_date="2026-01-18"))
    other = ledger.post(posting(account_id=second["id"], booked_date="2026-01-17"))
    assert [row["id"] for row in ledger.transactions(limit=2)] == [
        latest["id"],
        other["id"],
    ]
    assert [row["id"] for row in ledger.transactions(account_id=1)] == [
        latest["id"],
        first["id"],
    ]


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount_cents": True},
        {"amount_cents": 1.5},
        {"amount_cents": "100"},
        {"amount_cents": 0},
        {"amount_cents": -1},
        {"amount_cents": MAX_CENTS + 1},
        {"account_id": True},
        {"account_id": 0},
        {"category_id": False},
        {"category_id": -1},
        {"kind": "transfer_in"},
        {"booked_date": "2026-02-30"},
        {"booked_date": "20260116"},
        {"booked_date": datetime(2026, 1, 16)},
        {"booked_date": True},
        {"description": "s" * 2001},
        {"submission_id": "a" * 31},
        {"submission_id": "A" * 32},
        {"submission_id": "z" * 32},
        {"status": "posted"},
    ],
)
def test_invalid_posting_values_are_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        posting(**overrides)


def test_booking_date_defaults_to_today_in_berlin() -> None:
    before = datetime.now(ZoneInfo("Europe/Berlin")).date()
    values = posting().model_dump()
    del values["booked_date"]
    actual = PostingInput.model_validate(values).booked_date
    after = datetime.now(ZoneInfo("Europe/Berlin")).date()
    assert actual in (before, after)


@pytest.mark.parametrize(
    ("overrides", "archive", "field"),
    [
        ({"account_id": 999}, None, "account_id"),
        ({"category_id": 999}, None, "category_id"),
        ({}, "accounts", "account_id"),
        ({}, "categories", "category_id"),
        ({"category_id": 2}, None, "category_id"),
        ({"booked_date": "2026-01-14"}, None, "booked_date"),
    ],
)
def test_business_rules_reject_without_partial_writes(
    ledger: LedgerService,
    overrides: dict[str, object],
    archive: str | None,
    field: str,
) -> None:
    if archive is not None:
        CatalogService(ledger.database).set_active(archive, 1, False)
    with pytest.raises(LedgerError) as raised:
        ledger.post(posting(**overrides))
    assert raised.value.field == field
    assert counts(ledger) == (0, 0, 0)


@pytest.mark.parametrize("failure", ["allocation", "audit"])
def test_failure_rolls_back_transaction_allocation_and_audit(
    ledger: LedgerService, failure: str
) -> None:
    with ledger.database.connect() as connection:
        if failure == "allocation":
            connection.execute(
                "CREATE TRIGGER synthetic_failure BEFORE INSERT ON transaction_splits "
                "BEGIN SELECT RAISE(ABORT, 'synthetic allocation failure'); END"
            )
        else:
            connection.execute(
                "CREATE TRIGGER synthetic_failure BEFORE INSERT ON audit_log "
                "WHEN NEW.entity_type='transactions' "
                "BEGIN SELECT RAISE(ABORT, 'synthetic audit failure'); END"
            )
    values = posting()
    with pytest.raises(sqlite3.IntegrityError, match="synthetic"):
        ledger.post(values)
    assert counts(ledger) == (0, 0, 0)
    assert ledger.balance(1, date(2026, 1, 18)) == 10000
    with ledger.database.connect() as connection:
        connection.execute("DROP TRIGGER synthetic_failure")
    ledger.post(values)
    assert counts(ledger) == (1, 1, 1)


def test_identical_retry_is_idempotent_even_after_archiving(
    ledger: LedgerService,
) -> None:
    values = posting()
    first = ledger.post(values)
    CatalogService(ledger.database).set_active("accounts", 1, False)
    CatalogService(ledger.database).set_active("categories", 1, False)
    replayed = ledger.post(values)
    assert replayed["id"] == first["id"]
    assert counts(ledger) == (1, 1, 1)
    assert ledger.balance(1, date(2026, 1, 18)) == 11001


def test_reused_submission_with_different_content_conflicts(
    ledger: LedgerService,
) -> None:
    values = posting()
    ledger.post(values)
    with pytest.raises(LedgerError) as raised:
        ledger.post(values.model_copy(update={"amount_cents": 1002}))
    assert raised.value.conflict is True
    assert counts(ledger) == (1, 1, 1)
    assert ledger.balance(1, date(2026, 1, 18)) == 11001


def test_same_financial_content_with_new_submission_is_a_new_booking(
    ledger: LedgerService,
) -> None:
    ledger.post(posting())
    ledger.post(posting())
    assert counts(ledger) == (2, 2, 2)
    assert ledger.balance(1, date(2026, 1, 18)) == 12002


def test_concurrent_same_submission_creates_exactly_one_booking(
    ledger: LedgerService,
) -> None:
    values = posting()
    gate = Barrier(2)

    def post() -> dict:
        gate.wait(timeout=5)
        return ledger.post(values)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(post) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]
    assert results[0]["id"] == results[1]["id"]
    assert counts(ledger) == (1, 1, 1)
    assert ledger.balance(1, date(2026, 1, 18)) == 11001


def test_upgrade_from_v2_preserves_catalog_and_audit(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic-upgrade.sqlite3")
    migrate(database, MIGRATIONS[:2])
    catalog = CatalogService(database)
    original_account = create_account(catalog)
    original_category = catalog.create_category(
        CategoryInput(name="Synthetische Bestandskategorie", kind="income")
    )
    with database.connect() as connection:
        original_audit = [
            tuple(row)
            for row in connection.execute("SELECT * FROM audit_log ORDER BY id")
        ]
    assert migrate(database) == 3
    assert catalog.accounts() == [original_account]
    assert catalog.categories() == [original_category]
    upgraded = LedgerService(database)
    upgraded.post(posting())
    assert upgraded.balance(original_account["id"], date(2026, 1, 18)) == 11001
    with database.connect() as connection:
        retained_audit = [
            tuple(row)
            for row in connection.execute(
                "SELECT * FROM audit_log ORDER BY id LIMIT ?", (len(original_audit),)
            )
        ]
        assert retained_audit == original_audit
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
