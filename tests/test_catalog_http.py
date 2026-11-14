"""Formular-Endpunkte, CSRF und Pfade mit synthetischen Konten/Kategorien."""

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


def token(client: TestClient, prefix: str = "", headers: dict | None = None) -> str:
    response = client.get(f"{prefix}/bereiche/finanzen", headers=headers or {})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match is not None
    return match[1]


def account_form(csrf: str) -> dict[str, str]:
    return {
        "csrf_token": csrf,
        "name": "Synthetisches Testkonto",
        "account_type": "checking",
        "opening_balance": "-12,34",
        "opening_date": "2026-01-15",
        "notes": "synthetic note",
    }


@pytest.fixture(params=["", "/synthetic-ingress"])
def catalog_client(
    request: pytest.FixtureRequest, tmp_path: Path
) -> Iterator[tuple[TestClient, str, Database]]:
    database = Database(tmp_path / "synthetic.sqlite3")
    app = create_app(database_path=database.path)
    prefix = request.param
    if prefix:
        child = app

        @asynccontextmanager
        async def lifespan(parent: FastAPI):
            async with child.router.lifespan_context(child):
                yield

        parent = FastAPI(lifespan=lifespan)
        parent.mount(prefix, app)
        app = parent
    with TestClient(app) as client:
        yield client, prefix, database


def test_create_archive_and_reactivate_account(
    catalog_client: tuple[TestClient, str, Database],
) -> None:
    client, prefix, database = catalog_client
    csrf = token(client, prefix)
    response = client.post(
        f"{prefix}/konten", data=account_form(csrf), follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith(f"{prefix}/bereiche/finanzen")
    page = client.get(response.headers["location"])
    assert "-12,34 €" in page.text
    assert "Synthetisches Testkonto" in page.text
    with database.connect() as connection:
        assert (
            connection.execute("SELECT opening_balance_cents FROM accounts").fetchone()[
                0
            ]
            == -1234
        )
    for active in ("0", "1"):
        response = client.post(
            f"{prefix}/konten/1/status",
            data={"csrf_token": csrf, "active": active},
            follow_redirects=False,
        )
        assert response.status_code == 303


@pytest.mark.parametrize(
    "bad",
    [
        {"opening_balance": "1,001"},
        {"name": " "},
        {"opening_date": "2026-02-30"},
        {"account_type": "invalid"},
    ],
)
def test_invalid_form_preserves_values_without_mutation(
    catalog_client: tuple[TestClient, str, Database], bad: dict[str, str]
) -> None:
    client, prefix, database = catalog_client
    response = client.post(
        f"{prefix}/konten", data={**account_form(token(client, prefix)), **bad}
    )
    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM audit_log WHERE entity_type='accounts'"
            ).fetchone()[0]
            == 0
        )


@pytest.mark.parametrize(
    "attack", ["missing", "wrong", "origin", "fetch-site", "forged-forwarded-host"]
)
def test_foreign_or_missing_csrf_cannot_write(
    catalog_client: tuple[TestClient, str, Database], attack: str
) -> None:
    client, prefix, database = catalog_client
    form = account_form(token(client, prefix))
    headers = {}
    if attack == "missing":
        del form["csrf_token"]
    elif attack == "wrong":
        form["csrf_token"] = "synthetic-wrong-token"
    elif attack == "origin":
        headers["Origin"] = "https://example.invalid"
    elif attack == "fetch-site":
        headers["Sec-Fetch-Site"] = "cross-site"
    else:
        headers.update(
            {"Origin": "https://example.invalid", "X-Forwarded-Host": "example.invalid"}
        )
    response = client.post(f"{prefix}/konten", data=form, headers=headers)
    assert response.status_code == 403
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM audit_log WHERE entity_type='accounts'"
            ).fetchone()[0]
            == 0
        )


def test_categories_and_parent_validation(
    catalog_client: tuple[TestClient, str, Database],
) -> None:
    client, prefix, _ = catalog_client
    csrf = token(client, prefix)
    response = client.post(
        f"{prefix}/kategorien",
        data={
            "csrf_token": csrf,
            "name": "Synthetische Kategorie",
            "kind": "expense",
            "parent_id": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    response = client.post(
        f"{prefix}/kategorien",
        data={
            "csrf_token": csrf,
            "name": "Synthetische Unterkategorie",
            "kind": "income",
            "parent_id": "1",
        },
    )
    assert response.status_code == 422


def test_form_values_are_html_escaped(
    catalog_client: tuple[TestClient, str, Database],
) -> None:
    client, prefix, _ = catalog_client
    form = {**account_form(token(client, prefix)), "name": "<script>synthetic</script>"}
    response = client.post(f"{prefix}/konten", data=form)
    assert response.status_code == 200
    assert "&lt;script&gt;synthetic&lt;/script&gt;" in response.text
    assert "<script>synthetic</script>" not in response.text


def test_status_endpoint_cannot_overwrite_opening_balance(
    catalog_client: tuple[TestClient, str, Database],
) -> None:
    client, prefix, database = catalog_client
    csrf = token(client, prefix)
    client.post(f"{prefix}/konten", data=account_form(csrf))
    response = client.post(
        f"{prefix}/konten/1/status",
        data={"csrf_token": csrf, "active": "0", "opening_balance": "999,99"},
    )
    assert response.status_code == 400
    with database.connect() as connection:
        assert connection.execute(
            "SELECT opening_balance_cents, is_active FROM accounts"
        ).fetchone()[:] == (-1234, 1)


def test_verified_ingress_can_use_external_https_authority(tmp_path: Path) -> None:
    app = create_addon_app(database_path=tmp_path / "synthetic.sqlite3")
    prefix = "/api/hassio_ingress/synthetic-session"
    headers = {
        "X-Ingress-Path": prefix,
        "X-Forwarded-Host": "example.invalid",
        "X-Forwarded-Proto": "https",
        "Origin": "https://example.invalid",
    }
    with TestClient(app, client=("172.30.32.2", 12345)) as client:
        csrf = token(client, headers=headers)
        response = client.post(
            "/konten", headers=headers, data=account_form(csrf), follow_redirects=False
        )
        assert response.status_code == 303
        assert response.headers["location"].startswith(f"{prefix}/bereiche/finanzen")


def test_verified_ingress_accepts_no_referrer_form_origin(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    app = create_addon_app(database_path=database.path)
    headers = {"X-Ingress-Path": "/api/hassio_ingress/synthetic-session"}
    with TestClient(app, client=("172.30.32.2", 12345)) as client:
        csrf = token(client, headers=headers)
        post_headers = {**headers, "Origin": "null", "Sec-Fetch-Site": "same-origin"}
        response = client.post(
            "/konten",
            headers=post_headers,
            data=account_form(csrf),
            follow_redirects=False,
        )
        assert response.status_code == 303
        response = client.post(
            "/kategorien",
            headers=post_headers,
            data={"csrf_token": csrf, "name": "Synthetisch", "kind": "expense"},
            follow_redirects=False,
        )
        assert response.status_code == 303
        for path in ("/konten/1/status", "/kategorien/1/status"):
            for active in ("0", "1"):
                response = client.post(
                    path,
                    headers=post_headers,
                    data={"csrf_token": csrf, "active": active},
                    follow_redirects=False,
                )
                assert response.status_code == 303
    with database.connect() as connection:
        assert connection.execute(
            "SELECT opening_balance_cents, is_active FROM accounts"
        ).fetchone()[:] == (-1234, 1)
        assert connection.execute("SELECT is_active FROM categories").fetchone()[0] == 1
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM audit_log "
                "WHERE entity_type IN ('accounts', 'categories')"
            ).fetchone()[0]
            == 6
        )


@pytest.mark.parametrize(
    "attack",
    ["missing-token", "wrong-token", "cross-site", "same-site", "duplicate", "peer"],
)
def test_null_origin_does_not_bypass_ingress_or_csrf(
    tmp_path: Path, attack: str
) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    app = create_addon_app(database_path=database.path)
    headers = {"X-Ingress-Path": "/api/hassio_ingress/synthetic-session"}
    with TestClient(app, client=("172.30.32.2", 12345)) as trusted:
        form = account_form(token(trusted, headers=headers))
        post_headers = [*headers.items(), ("Origin", "null")]
        if attack == "missing-token":
            del form["csrf_token"]
        elif attack == "wrong-token":
            form["csrf_token"] = "synthetic-wrong"
        elif attack in ("cross-site", "same-site"):
            post_headers.append(("Sec-Fetch-Site", attack))
        elif attack == "duplicate":
            post_headers.append(("Origin", "null"))
        if attack == "peer":
            post_headers.append(("X-Forwarded-For", "172.30.32.2"))
            with TestClient(app, client=("172.30.32.4", 12345)) as untrusted:
                response = untrusted.post("/konten", headers=post_headers, data=form)
        else:
            response = trusted.post("/konten", headers=post_headers, data=form)
        assert response.status_code == 403
        with database.connect() as connection:
            assert (
                connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0
            )
            assert (
                connection.execute(
                    "SELECT COUNT(*) FROM audit_log WHERE entity_type='accounts'"
                ).fetchone()[0]
                == 0
            )


@pytest.mark.parametrize(
    "origin",
    [
        "https://testserver:0",
        "https://testserver/path",
        "null",
        "https://testserver:65536",
    ],
)
def test_malformed_origin_authority_is_rejected(
    catalog_client: tuple[TestClient, str, Database], origin: str
) -> None:
    client, prefix, database = catalog_client
    response = client.post(
        f"{prefix}/konten",
        data=account_form(token(client, prefix)),
        headers={"Origin": origin},
    )
    assert response.status_code == 403
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0


def test_json_form_encoding_is_rejected(
    catalog_client: tuple[TestClient, str, Database],
) -> None:
    client, prefix, _ = catalog_client
    response = client.post(f"{prefix}/konten", json=account_form(token(client, prefix)))
    assert response.status_code == 415


@pytest.mark.parametrize(
    ("mode", "expected"), [("large", 413), ("duplicate", 400), ("utf8", 400)]
)
def test_form_limits_and_duplicate_fields(
    catalog_client: tuple[TestClient, str, Database], mode: str, expected: int
) -> None:
    client, prefix, database = catalog_client
    csrf = token(client, prefix)
    extra = {
        "large": "name=" + "s" * 40000,
        "duplicate": "name=synthetic&name=other",
        "utf8": "name=%FF",
    }[mode]
    response = client.post(
        f"{prefix}/konten",
        content=f"csrf_token={csrf}&{extra}",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == expected
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0


def test_early_year_is_displayed_with_four_digits(
    catalog_client: tuple[TestClient, str, Database],
) -> None:
    client, prefix, _ = catalog_client
    form = {**account_form(token(client, prefix)), "opening_date": "0001-01-01"}
    response = client.post(f"{prefix}/konten", data=form)
    assert response.status_code == 200
    assert "01.01.0001" in response.text


@pytest.mark.parametrize(
    "forwarded", ["example.invalid,other.invalid", "example.invalid:0"]
)
def test_verified_ingress_rejects_ambiguous_forwarded_authority(
    tmp_path: Path, forwarded: str
) -> None:
    app = create_addon_app(database_path=tmp_path / "synthetic.sqlite3")
    headers = {"X-Ingress-Path": "/api/hassio_ingress/synthetic-session"}
    with TestClient(app, client=("172.30.32.2", 12345)) as client:
        form = account_form(token(client, headers=headers))
        response = client.post(
            "/konten",
            data=form,
            headers={
                **headers,
                "Origin": "https://example.invalid",
                "X-Forwarded-Host": forwarded,
            },
        )
        assert response.status_code == 403
