"""Buchungsformulare, Präfixe und Schutz mit synthetischen Daten."""

import re
from collections.abc import Iterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lebensassistent.database.connection import Database
from lebensassistent.integrations.homeassistant.ingress import create_addon_app
from lebensassistent.main import create_app
from lebensassistent.services.catalog import AccountInput, CatalogService, CategoryInput


def prepare(database: Database) -> None:
    catalog = CatalogService(database)
    catalog.create_account(
        AccountInput(
            name="Synthetisches Buchungskonto",
            account_type="checking",
            opening_balance_cents=10000,
            opening_date="2026-01-01",
        )
    )
    for kind in ("expense", "income"):
        catalog.create_category(CategoryInput(name=f"Synthetisch {kind}", kind=kind))


def form(client: TestClient, prefix: str = "", headers: dict | None = None) -> dict:
    page = client.get(f"{prefix}/bereiche/finanzen", headers=headers or {})
    assert page.status_code == 200
    values = {}
    for name in ("csrf_token", "submission_id"):
        match = re.search(rf'name="{name}" value="([^"]+)"', page.text)
        assert match is not None
        values[name] = match[1]
    return {
        **values,
        "kind": "expense",
        "account_id": "1",
        "category_id": "1",
        "amount": "12,34",
        "booked_date": "2026-01-15",
        "description": "Synthetische Testbuchung",
    }


@pytest.fixture(params=["", "/synthetic-ingress"])
def ledger_client(
    tmp_path: Path, request: pytest.FixtureRequest
) -> Iterator[tuple[TestClient, str, Database]]:
    database = Database(tmp_path / "synthetic.sqlite3")
    child = create_app(database_path=database.path)
    prefix = request.param
    if prefix:

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with child.router.lifespan_context(child):
                yield

        app = FastAPI(lifespan=lifespan)
        app.mount(prefix, child)
    else:
        app = child
    with TestClient(app) as client:
        prepare(database)
        yield client, prefix, database


def test_post_and_reload_do_not_duplicate_booking(ledger_client: tuple) -> None:
    client, prefix, database = ledger_client
    values = form(client, prefix)
    for _ in range(2):
        result = client.post(f"{prefix}/buchungen", data=values, follow_redirects=False)
        assert result.status_code == 303
        assert result.headers["location"].startswith(f"{prefix}/bereiche/finanzen")
        assert result.headers["cache-control"] == "no-store"
    page = client.get(result.headers["location"])
    assert "87,66 €" in page.text
    assert "Synthetische Testbuchung" in page.text
    with database.connect() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM transaction_splits").fetchone()[0]
            == 1
        )


@pytest.mark.parametrize(
    "bad",
    [
        {"amount": "0"},
        {"amount": "-1"},
        {"amount": "1,001"},
        {"kind": "transfer_out"},
        {"category_id": "2"},
        {"account_id": "999"},
        {"booked_date": "2025-12-31"},
        {"booked_date": "2026-02-30"},
        {"submission_id": "invalid"},
    ],
)
def test_invalid_booking_preserves_form_without_writing(
    ledger_client: tuple, bad: dict
) -> None:
    client, prefix, database = ledger_client
    values = {**form(client, prefix), **bad}
    page = client.post(f"{prefix}/buchungen", data=values)
    assert page.status_code == 422
    assert page.headers["cache-control"] == "no-store"
    assert "Synthetische Testbuchung" in page.text
    assert f'name="submission_id" value="{values["submission_id"]}"' in page.text
    with database.connect() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
        )


def test_default_date_and_html_escaping(ledger_client: tuple) -> None:
    client, prefix, database = ledger_client
    values = form(client, prefix)
    del values["booked_date"]
    values["description"] = "<script>syntheticAttack()</script>"
    page = client.post(f"{prefix}/buchungen", data=values)
    assert page.status_code == 200
    assert "&lt;script&gt;syntheticAttack()&lt;/script&gt;" in page.text
    assert "<script>syntheticAttack()</script>" not in page.text
    with database.connect() as connection:
        value = connection.execute("SELECT booked_date FROM transactions").fetchone()[0]
    from lebensassistent.services.ledger import today_berlin

    assert value == today_berlin().isoformat()


@pytest.mark.parametrize("attack", ["token", "origin", "fetch-site", "json"])
def test_booking_security_checks_precede_writes(
    ledger_client: tuple, attack: str
) -> None:
    client, prefix, database = ledger_client
    values = form(client, prefix)
    headers = {}
    if attack == "token":
        values["csrf_token"] = "synthetic-wrong"
    elif attack == "origin":
        headers["Origin"] = "https://synthetic.invalid"
    elif attack == "fetch-site":
        headers["Sec-Fetch-Site"] = "cross-site"
    result = client.post(
        f"{prefix}/buchungen",
        headers=headers,
        **({"json": values} if attack == "json" else {"data": values}),
    )
    assert result.status_code == (415 if attack == "json" else 403)
    with database.connect() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
        )


def test_booking_works_with_verified_ingress_and_null_origin(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    app = create_addon_app(database_path=database.path)
    headers = {
        "X-Ingress-Path": "/api/hassio_ingress/synthetic-session",
        "Origin": "null",
        "Sec-Fetch-Site": "same-origin",
    }
    with TestClient(app, client=("172.30.32.2", 12345)) as client:
        prepare(database)
        values = form(client, headers=headers)
        result = client.post(
            "/buchungen", headers=headers, data=values, follow_redirects=False
        )
        assert result.status_code == 303


def test_submission_id_cannot_be_reused_for_different_amount(
    ledger_client: tuple,
) -> None:
    client, prefix, database = ledger_client
    values = form(client, prefix)
    assert client.post(f"{prefix}/buchungen", data=values).status_code == 200
    result = client.post(f"{prefix}/buchungen", data={**values, "amount": "99,99"})
    assert result.status_code == 409
    with database.connect() as connection:
        assert (
            connection.execute("SELECT amount_cents FROM transactions").fetchone()[0]
            == 1234
        )
