"""Start und Neustart nur mit temporären SQLite-Dateien."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lebensassistent.database.connection import Database
from lebensassistent.database.migrations import MIGRATIONS, MigrationError, migrate
from lebensassistent.integrations.homeassistant.ingress import create_addon_app
from lebensassistent.main import create_app


def test_app_initializes_database_and_repeated_start_keeps_history(
    tmp_path: Path,
) -> None:
    path = tmp_path / "synthetic.sqlite3"
    for _ in range(2):
        app = create_app(database_path=path)
        with TestClient(app) as client:
            assert client.get("/health").json() == {"status": "ok"}
            assert app.state.database.path == path
    with Database(path).connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM audit_log").fetchone()[
            0
        ] == len(MIGRATIONS)


def test_corrupt_database_prevents_start_without_overwriting_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "synthetic.sqlite3"
    contents = b"synthetic invalid SQLite content"
    path.write_bytes(contents)
    with (
        pytest.raises(sqlite3.DatabaseError),
        TestClient(create_app(database_path=path)),
    ):
        pytest.fail("Corrupt database must prevent startup")
    assert path.read_bytes() == contents


def test_future_database_prevents_app_start(tmp_path: Path) -> None:
    database = Database(tmp_path / "synthetic.sqlite3")
    migrate(database)
    with database.connect() as connection:
        connection.execute(
            "UPDATE schema_migrations SET version = 999 "
            "WHERE version = (SELECT MAX(version) FROM schema_migrations)"
        )
    with (
        pytest.raises(MigrationError),
        TestClient(create_app(database_path=database.path)),
    ):
        pytest.fail("Unsupported database must prevent startup")


def test_ha_app_initializes_database_behind_existing_ingress_guard(
    tmp_path: Path,
) -> None:
    path = tmp_path / "synthetic.sqlite3"
    app = create_addon_app(database_path=path)
    with TestClient(app, client=("172.30.32.2", 12345)) as client:
        response = client.get(
            "/health",
            headers={"X-Ingress-Path": "/api/hassio_ingress/synthetic-session"},
        )
        assert response.json() == {"status": "ok"}
    assert path.is_file()


def test_default_app_factory_has_no_database_side_effect() -> None:
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert not hasattr(app.state, "database")


def test_cli_migrates_database_without_user_or_finance_data(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.sqlite3"
    result = subprocess.run(
        [sys.executable, "-m", "lebensassistent.database", "--path", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert f"schema version {len(MIGRATIONS)}" in result.stdout
    with Database(path).connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM audit_log").fetchone()[
            0
        ] == len(MIGRATIONS)


def test_local_data_directory_is_explicitly_configurable(tmp_path: Path) -> None:
    script = """
from fastapi.testclient import TestClient
from lebensassistent.main import app
with TestClient(app) as client:
    assert client.get('/health').status_code == 200
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "LEBENSASSISTENT_DATA_DIR": str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    assert (tmp_path / "lebensassistent.sqlite3").is_file()
