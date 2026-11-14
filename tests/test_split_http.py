"""Aufteilungsformulare mit synthetischen Kategorien, Beträgen und Präfixen."""

import re
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lebensassistent.database.connection import Database
from lebensassistent.integrations.homeassistant.ingress import create_addon_app
from lebensassistent.main import create_app
from lebensassistent.services.catalog import AccountInput, CatalogService, CategoryInput

PATH = "/buchungen/aufteilen"


def prepare(database: Database) -> None:
    catalog = CatalogService(database)
    catalog.create_account(
        AccountInput(
            name="Synthetisches Splitkonto",
            account_type="checking",
            opening_balance_cents=10000,
            opening_date="2026-01-01",
        )
    )
    for name, kind in (
        ("Synthetisch A", "expense"),
        ("Synthetisch B", "expense"),
        ("Synthetisch C", "income"),
    ):
        catalog.create_category(CategoryInput(name=name, kind=kind))


def form(client: TestClient, prefix: str = "", headers: dict | None = None) -> dict:
    page = client.get(prefix + PATH, headers=headers or {})
    assert page.status_code == 200
    assert page.headers["cache-control"] == "no-store"
    hidden = {}
    for name in ("csrf_token", "submission_id", "row_count"):
        match = re.search(rf'name="{name}" value="([^"]+)"', page.text)
        assert match is not None
        hidden[name] = match[1]
    return {
        **hidden,
        "intent": "save",
        "kind": "expense",
        "account_id": "1",
        "amount": "100,00",
        "booked_date": "2026-01-15",
        "description": "Synthetische Aufteilung",
        "category_0": "1",
        "amount_0": "70,00",
        "memo_0": "<b>Synthetische Teilnotiz</b>",
        "category_1": "2",
        "amount_1": "30,00",
        "memo_1": "Synthetische zweite Teilnotiz",
    }


@pytest.fixture(params=["", "/synthetic-ingress"])
def client_data(tmp_path: Path, request: pytest.FixtureRequest):
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


def test_split_saves_once_and_displays_every_allocation(client_data: tuple) -> None:
    client, prefix, database = client_data
    values = form(client, prefix)
    for _ in range(2):
        result = client.post(prefix + PATH, data=values, follow_redirects=False)
        assert result.status_code == 303
        assert result.headers["location"].startswith(prefix + "/bereiche/finanzen")
    page = client.get(result.headers["location"])
    assert "0,00 €" in page.text
    for text in (
        "70,00 €",
        "30,00 €",
        "Synthetisch A",
        "Synthetisch B",
        "&lt;b&gt;Synthetische Teilnotiz&lt;/b&gt;",
    ):
        assert text in page.text
    assert "<b>Synthetische Teilnotiz</b>" not in page.text
    with database.connect() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM transaction_splits").fetchone()[0]
            == 2
        )
    conflict = client.post(
        prefix + PATH, data={**values, "memo_1": "Synthetisch anders"}
    )
    assert conflict.status_code == 409


@pytest.mark.parametrize(
    "bad",
    [
        {"amount_1": "29,99"},
        {"amount_1": "30,01"},
        {"amount_0": "0"},
        {"amount_0": "-1"},
        {"amount_1": "1,001"},
        {"category_1": "3"},
        {"category_1": "999"},
        {"amount_1": ""},
        {"category_1": ""},
        {"memo_1": "s" * 2001},
        {"booked_date": "2025-12-31"},
    ],
)
def test_invalid_split_preserves_rows_and_submission(
    client_data: tuple, bad: dict
) -> None:
    client, prefix, database = client_data
    values = {**form(client, prefix), **bad}
    response = client.post(prefix + PATH, data=values)
    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    assert "Synthetische Aufteilung" in response.text
    assert f'name="submission_id" value="{values["submission_id"]}"' in response.text
    assert f'name="amount_0" value="{values["amount_0"]}"' in response.text
    with database.connect() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM transaction_splits").fetchone()[0]
            == 0
        )


def test_add_remove_only_changes_form_and_keeps_other_rows(client_data: tuple) -> None:
    client, prefix, database = client_data
    values = form(client, prefix)
    response = client.post(prefix + PATH, data={**values, "intent": "add"})
    assert response.status_code == 200
    assert 'name="row_count" value="3"' in response.text
    values.update(
        row_count="3", category_2="2", amount_2="20,00", memo_2="Synthetisch behalten"
    )
    response = client.post(prefix + PATH, data={**values, "intent": "remove:1"})
    assert response.status_code == 200
    assert 'name="row_count" value="2"' in response.text
    assert 'name="amount_1" value="20,00"' in response.text
    assert "Synthetisch behalten" in response.text
    assert 'name="amount_2"' not in response.text
    with database.connect() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
        )


@pytest.mark.parametrize("attack", ["token", "cross-site", "null", "json", "large"])
def test_split_protection_precedes_any_write(client_data: tuple, attack: str) -> None:
    client, prefix, database = client_data
    values = form(client, prefix)
    headers = {}
    if attack == "token":
        values["csrf_token"] = "synthetic-wrong"
        values["intent"] = "add"
    elif attack == "cross-site":
        headers["Sec-Fetch-Site"] = "cross-site"
    elif attack == "null":
        headers["Origin"] = "null"
    elif attack == "large":
        values["memo_0"] = "s" * 40000
    response = client.post(
        prefix + PATH,
        headers=headers,
        **({"json": values} if attack == "json" else {"data": values}),
    )
    assert response.status_code == {"json": 415, "large": 413}.get(attack, 403)
    with database.connect() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
        )


@pytest.mark.parametrize(
    "bad",
    [
        {"row_count": "1"},
        {"row_count": "21"},
        {"row_count": "bad"},
        {"category_2": "1"},
        {"intent": "remove:-1"},
        {"intent": "remove:2"},
        {"intent": "unknown"},
    ],
)
def test_malformed_row_controls_rejected(client_data: tuple, bad: dict) -> None:
    client, prefix, _ = client_data
    assert (
        client.post(prefix + PATH, data={**form(client, prefix), **bad}).status_code
        == 400
    )


def test_twenty_rows_fit_explicit_parser_budget(client_data: tuple) -> None:
    client, prefix, database = client_data
    values = {**form(client, prefix), "row_count": "20", "amount": "20,00"}
    for index in range(20):
        values.update(
            {f"category_{index}": "1", f"amount_{index}": "1,00", f"memo_{index}": ""}
        )
    assert (
        client.post(prefix + PATH, data=values, follow_redirects=False).status_code
        == 303
    )
    with database.connect() as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM transaction_splits").fetchone()[0]
            == 20
        )


def test_split_with_verified_ingress_null_origin(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    app = create_addon_app(database_path=database.path)
    headers = {
        "X-Ingress-Path": "/api/hassio_ingress/synthetic-session",
        "Origin": "null",
    }
    with TestClient(app, client=("172.30.32.2", 12345)) as client:
        prepare(database)
        assert (
            client.post(
                PATH,
                headers=headers,
                data=form(client, headers=headers),
                follow_redirects=False,
            ).status_code
            == 303
        )
