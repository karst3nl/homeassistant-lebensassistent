"""Centgenaue, atomare Aufteilungen mit ausschließlich synthetischen Daten."""

import json
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from threading import Barrier

import pytest
from pydantic import ValidationError

from lebensassistent.database.connection import Database
from lebensassistent.database.migrations import MIGRATIONS, migrate
from lebensassistent.services.catalog import AccountInput, CatalogService, CategoryInput
from lebensassistent.services.ledger import (
    LedgerError,
    LedgerService,
    PostingInput,
    SplitInput,
    SplitPostingInput,
)
from lebensassistent.services.values import MAX_CENTS


@pytest.fixture
def ledger(tmp_path: Path) -> LedgerService:
    database = Database(tmp_path / "synthetic-splits.sqlite3")
    migrate(database)
    catalog = CatalogService(database)
    catalog.create_account(
        AccountInput(
            name="Synthetisches Splitkonto",
            account_type="checking",
            opening_balance_cents=50000,
            opening_date="2026-01-01",
        )
    )
    for name, kind in (
        ("Synthetische Ausgabe A", "expense"),
        ("Synthetische Ausgabe B", "expense"),
        ("Synthetische Einnahme A", "income"),
        ("Synthetische Einnahme B", "income"),
    ):
        catalog.create_category(CategoryInput(name=name, kind=kind))
    return LedgerService(database)


def posting(**overrides: object) -> SplitPostingInput:
    return SplitPostingInput.model_validate(
        {
            "account_id": 1,
            "kind": "expense",
            "amount_cents": 10000,
            "booked_date": "2026-01-15",
            "description": "Synthetisch aufgeteilte Buchung",
            "submission_id": uuid.uuid4().hex,
            "splits": [
                {
                    "category_id": 1,
                    "amount_cents": 7000,
                    "memo": "Synthetischer Anteil A",
                },
                {
                    "category_id": 2,
                    "amount_cents": 3000,
                    "memo": "Synthetischer Anteil B",
                },
            ],
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


@pytest.mark.parametrize("kind", ["expense", "income"])
def test_split_posts_once_with_exact_sum_and_full_audit(
    ledger: LedgerService, kind: str
) -> None:
    categories = (1, 2) if kind == "expense" else (3, 4)
    values = posting(
        kind=kind,
        splits=[
            {"category_id": categories[0], "amount_cents": 7000, "memo": "Anteil A"},
            {"category_id": categories[1], "amount_cents": 3000, "memo": "Anteil B"},
        ],
    )
    result = ledger.post_split(values)
    assert result["amount_cents"] == 10000
    assert [part["amount_cents"] for part in result["splits"]] == [7000, 3000]
    assert [part["sort_order"] for part in result["splits"]] == [0, 1]
    assert counts(ledger) == (1, 2, 1)
    assert ledger.balance(1, date(2026, 1, 15)) == (
        40000 if kind == "expense" else 60000
    )
    with ledger.database.connect() as connection:
        audit = connection.execute(
            "SELECT action, after_json FROM audit_log WHERE entity_type='transactions'"
        ).fetchone()
    snapshot = json.loads(audit["after_json"])
    assert audit["action"] == "create"
    assert snapshot["id"] == result["id"]
    assert snapshot["amount_cents"] == 10000
    assert [
        (part["category_id"], part["amount_cents"], part["memo"])
        for part in snapshot["splits"]
    ] == [(categories[0], 7000, "Anteil A"), (categories[1], 3000, "Anteil B")]


@pytest.mark.parametrize("difference", [-1, 1])
def test_one_cent_difference_is_rejected(difference: int) -> None:
    with pytest.raises(ValidationError):
        posting(amount_cents=10000 + difference)


def test_service_sum_guard_covers_model_copy(ledger: LedgerService) -> None:
    values = posting().model_copy(update={"amount_cents": 10001})
    with pytest.raises(LedgerError) as raised:
        ledger.post_split(values)
    assert raised.value.field == "splits"
    assert counts(ledger) == (0, 0, 0)


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount_cents": 0},
        {"amount_cents": -1},
        {"amount_cents": 1.5},
        {"amount_cents": True},
        {"amount_cents": "10000"},
        {"amount_cents": MAX_CENTS + 1},
        {"category_id": 0},
        {"category_id": True},
        {"category_id": "1"},
        {"memo": "s" * 2001},
        {"memo": False},
        {"memo": 12},
        {"unexpected": "synthetic"},
    ],
)
def test_invalid_split_values_are_rejected(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        SplitInput.model_validate({"category_id": 1, "amount_cents": 1, **overrides})


@pytest.mark.parametrize(
    "overrides",
    [
        {"splits": []},
        {"splits": [{"category_id": 1, "amount_cents": 10000}]},
        {"splits": [{"category_id": 1, "amount_cents": 1}] * 21, "amount_cents": 21},
        {"splits": "synthetic"},
        {"category_id": 1},
        {"kind": "transfer_out"},
        {"account_id": True},
        {"booked_date": "2026-02-30"},
        {"submission_id": "synthetic-invalid"},
    ],
)
def test_invalid_split_posting_is_rejected(overrides: dict) -> None:
    with pytest.raises(ValidationError):
        posting(**overrides)


def test_twenty_parts_of_one_cent_and_repeated_categories_are_allowed(
    ledger: LedgerService,
) -> None:
    values = posting(
        amount_cents=20,
        splits=[{"category_id": 1, "amount_cents": 1, "memo": "s" * 2000}] * 20,
    )
    result = ledger.post_split(values)
    assert len(result["splits"]) == 20
    assert sum(part["amount_cents"] for part in result["splits"]) == 20
    assert counts(ledger) == (1, 20, 1)
    assert ledger.balance(1, date(2026, 1, 15)) == 49980


def test_maximum_amount_and_overlarge_part_sum_are_exact(ledger: LedgerService) -> None:
    values = posting(
        amount_cents=MAX_CENTS,
        splits=[
            {"category_id": 1, "amount_cents": MAX_CENTS - 1},
            {"category_id": 2, "amount_cents": 1},
        ],
    )
    ledger.post_split(values)
    assert ledger.balance(1, date(2026, 1, 15)) == 50000 - MAX_CENTS
    ledger.post_split(values.model_copy(update={"submission_id": uuid.uuid4().hex}))
    assert ledger.balance(1, date(2026, 1, 15)) == 50000 - 2 * MAX_CENTS
    with pytest.raises(ValidationError):
        posting(
            amount_cents=MAX_CENTS,
            splits=[
                {"category_id": 1, "amount_cents": MAX_CENTS},
                {"category_id": 2, "amount_cents": MAX_CENTS},
            ],
        )


@pytest.mark.parametrize("invalid", ["missing", "archived", "wrong-kind"])
def test_each_category_is_checked_before_any_write(
    ledger: LedgerService, invalid: str
) -> None:
    category_id = {"missing": 999, "archived": 2, "wrong-kind": 3}[invalid]
    if invalid == "archived":
        CatalogService(ledger.database).set_active("categories", 2, False)
    values = posting(
        splits=[
            {"category_id": 1, "amount_cents": 7000},
            {"category_id": category_id, "amount_cents": 3000},
        ]
    )
    with pytest.raises(LedgerError) as raised:
        ledger.post_split(values)
    assert raised.value.field == "splits.1.category_id"
    assert counts(ledger) == (0, 0, 0)


@pytest.mark.parametrize(
    "invalid", ["missing-account", "archived-account", "before-opening"]
)
def test_account_and_date_rules_are_unchanged(
    ledger: LedgerService, invalid: str
) -> None:
    if invalid == "archived-account":
        CatalogService(ledger.database).set_active("accounts", 1, False)
    values = posting(
        **(
            {"account_id": 999}
            if invalid == "missing-account"
            else {"booked_date": "2025-12-31"}
            if invalid == "before-opening"
            else {}
        )
    )
    with pytest.raises(LedgerError):
        ledger.post_split(values)
    assert counts(ledger) == (0, 0, 0)


@pytest.mark.parametrize("failure", ["second-split", "audit"])
def test_late_failure_rolls_back_all_parts_and_parent(
    ledger: LedgerService, failure: str
) -> None:
    with ledger.database.connect() as connection:
        table, condition = (
            ("transaction_splits", "NEW.sort_order = 1")
            if failure == "second-split"
            else ("audit_log", "NEW.entity_type='transactions'")
        )
        connection.execute(
            f"CREATE TRIGGER synthetic_split_failure BEFORE INSERT ON {table} "
            f"WHEN {condition} "
            "BEGIN SELECT RAISE(ABORT, 'synthetic split failure'); END"
        )
    values = posting()
    with pytest.raises(sqlite3.IntegrityError, match="synthetic split failure"):
        ledger.post_split(values)
    assert counts(ledger) == (0, 0, 0)
    assert ledger.balance(1, date(2026, 1, 15)) == 50000
    with ledger.database.connect() as connection:
        connection.execute("DROP TRIGGER synthetic_split_failure")
    ledger.post_split(values)
    assert counts(ledger) == (1, 2, 1)


def test_query_limits_parents_and_returns_all_ordered_parts(
    ledger: LedgerService,
) -> None:
    first = ledger.post_split(posting(booked_date="2026-01-15"))
    second = ledger.post_split(posting(booked_date="2026-01-16"))
    third = ledger.post_split(posting(booked_date="2026-01-17"))
    records = ledger.transactions(account_id=1, limit=2)
    assert [record["id"] for record in records] == [third["id"], second["id"]]
    assert first["id"] not in [record["id"] for record in records]
    for record in records:
        assert record["category_id"] is None
        assert record["category_name"] == "Aufgeteilte Buchung"
        assert [part["sort_order"] for part in record["splits"]] == [0, 1]
        assert [part["category_name"] for part in record["splits"]] == [
            "Synthetische Ausgabe A",
            "Synthetische Ausgabe B",
        ]
        assert [part["memo"] for part in record["splits"]] == [
            "Synthetischer Anteil A",
            "Synthetischer Anteil B",
        ]
    assert ledger.balance(1, date(2026, 1, 17)) == 20000


def test_identical_replay_after_archiving_keeps_one_parent(
    ledger: LedgerService,
) -> None:
    values = posting()
    first = ledger.post_split(values)
    catalog = CatalogService(ledger.database)
    catalog.set_active("accounts", 1, False)
    catalog.set_active("categories", 2, False)
    replay = ledger.post_split(values)
    assert replay["id"] == first["id"]
    assert counts(ledger) == (1, 2, 1)
    assert ledger.balance(1, date(2026, 1, 15)) == 40000


@pytest.mark.parametrize("changed", ["memo", "amounts", "category", "order"])
def test_reused_key_with_changed_allocation_conflicts(
    ledger: LedgerService, changed: str
) -> None:
    values = posting()
    ledger.post_split(values)
    parts = [part.model_dump() for part in values.splits]
    if changed == "memo":
        parts[1]["memo"] = "Synthetisch geändert"
    elif changed == "amounts":
        parts[0]["amount_cents"], parts[1]["amount_cents"] = 6000, 4000
    elif changed == "category":
        parts[1]["category_id"] = 1
    else:
        parts.reverse()
    altered = SplitPostingInput.model_validate({**values.model_dump(), "splits": parts})
    with pytest.raises(LedgerError) as raised:
        ledger.post_split(altered)
    assert raised.value.conflict is True
    assert counts(ledger) == (1, 2, 1)


def test_concurrent_identical_submission_is_stored_once(ledger: LedgerService) -> None:
    values = posting()
    gate = Barrier(2)

    def post() -> dict:
        gate.wait(timeout=5)
        return ledger.post_split(values)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [
            future.result(timeout=10)
            for future in [pool.submit(post), pool.submit(post)]
        ]
    assert results[0]["id"] == results[1]["id"]
    assert counts(ledger) == (1, 2, 1)
    assert ledger.balance(1, date(2026, 1, 15)) == 40000


def test_concurrent_conflicting_submission_has_one_complete_winner(
    ledger: LedgerService,
) -> None:
    first = posting()
    second = SplitPostingInput.model_validate(
        {
            **first.model_dump(),
            "splits": [
                {"category_id": 1, "amount_cents": 6000},
                {"category_id": 2, "amount_cents": 4000},
            ],
        }
    )
    gate = Barrier(2)

    def post(values: SplitPostingInput) -> dict | LedgerError:
        gate.wait(timeout=5)
        try:
            return ledger.post_split(values)
        except LedgerError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(post, values) for values in (first, second)]
        results = [future.result(timeout=10) for future in futures]
    winners = [result for result in results if isinstance(result, dict)]
    conflicts = [result for result in results if isinstance(result, LedgerError)]
    assert len(winners) == len(conflicts) == 1
    assert conflicts[0].conflict is True
    assert counts(ledger) == (1, 2, 1)
    assert [part["amount_cents"] for part in ledger.transactions()[0]["splits"]] == [
        part["amount_cents"] for part in winners[0]["splits"]
    ]
    assert ledger.balance(1, date(2026, 1, 15)) == 40000


def test_archive_race_serializes_with_whole_posting(ledger: LedgerService) -> None:
    gate = Barrier(2)
    values = posting()

    def post() -> dict | LedgerError:
        gate.wait(timeout=5)
        try:
            return ledger.post_split(values)
        except LedgerError as error:
            return error

    def archive() -> dict:
        gate.wait(timeout=5)
        return CatalogService(ledger.database).set_active("categories", 2, False)

    with ThreadPoolExecutor(max_workers=2) as pool:
        posted, archived = pool.submit(post), pool.submit(archive)
        result = posted.result(timeout=10)
        assert archived.result(timeout=10)["is_active"] == 0
    if isinstance(result, LedgerError):
        assert result.field == "splits.1.category_id"
        assert counts(ledger) == (0, 0, 0)
        assert ledger.balance(1, date(2026, 1, 15)) == 50000
    else:
        assert counts(ledger) == (1, 2, 1)
        assert ledger.balance(1, date(2026, 1, 15)) == 40000


def test_schema_three_normal_posting_remains_unchanged(ledger: LedgerService) -> None:
    assert len(MIGRATIONS) == 3
    normal = ledger.post(
        PostingInput(
            account_id=1,
            category_id=1,
            kind="expense",
            amount_cents=123,
            booked_date="2026-01-14",
            submission_id=uuid.uuid4().hex,
        )
    )
    with ledger.database.connect() as connection:
        versions = [
            tuple(row) for row in connection.execute("SELECT * FROM schema_migrations")
        ]
        old_audit = [
            tuple(row)
            for row in connection.execute("SELECT * FROM audit_log ORDER BY id")
        ]
    ledger.post_split(posting())
    records = ledger.transactions()
    preserved = next(record for record in records if record["id"] == normal["id"])
    assert preserved["amount_cents"] == 123
    assert preserved["category_id"] == 1
    assert preserved["category_name"] == "Synthetische Ausgabe A"
    assert len(preserved["splits"]) == 1
    assert counts(ledger) == (2, 3, 2)
    assert ledger.balance(1, date(2026, 1, 15)) == 39877
    with ledger.database.connect() as connection:
        assert [
            tuple(row) for row in connection.execute("SELECT * FROM schema_migrations")
        ] == versions
        assert [
            tuple(row)
            for row in connection.execute(
                "SELECT * FROM audit_log ORDER BY id LIMIT ?", (len(old_audit),)
            )
        ] == old_audit
