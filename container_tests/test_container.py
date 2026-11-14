"""Reale Container: TCP-Vertrauenskette, Rechte, Lebenszyklus und Testpersistenz."""

import json
import re

from container_tests.conftest import PREFIX, DockerSandbox


def test_real_tcp_peer_and_proxy_header_forgery(sandbox: DockerSandbox) -> None:
    headers = {"X-Ingress-Path": PREFIX}
    response = sandbox.request(sandbox.trusted, "/", headers)
    assert response["status"] == 200
    assert f'href="{PREFIX}/static/styles.css"' in response["body"]
    assert (
        sandbox.request(sandbox.trusted, "/static/styles.css", headers)["status"] == 200
    )
    assert sandbox.request(sandbox.trusted, "/", {})["status"] == 400

    forged = {
        **headers,
        "X-Forwarded-For": "172.30.32.2",
        "X-Remote-User-Id": "synthetic-user",
    }
    for path in ("/", "/health", "/static/styles.css"):
        assert sandbox.request(sandbox.untrusted, path, forged)["status"] == 403
    response = sandbox.request(sandbox.trusted, "/bereiche/finanzen/", headers)
    assert response["status"] == 307
    assert response["headers"]["location"] == f"{PREFIX}/bereiche/finanzen"


def test_runtime_is_unprivileged_without_public_ports_or_dev_tools(
    sandbox: DockerSandbox,
) -> None:
    info = json.loads(sandbox.docker("inspect", sandbox.app).stdout)[0]
    assert not info["HostConfig"]["PortBindings"]
    assert info["HostConfig"]["ReadonlyRootfs"] is True
    code = """
import importlib.util
import shutil
from pathlib import Path
status = Path('/proc/1/status').read_text()
assert 'Uid:\\t1000\\t1000\\t1000\\t1000' in status
assert 'Gid:\\t1000\\t1000\\t1000\\t1000' in status
data = Path('/data').stat()
assert data.st_uid == data.st_gid == 1000
assert data.st_mode & 0o777 == 0o700
for name in ('pytest', 'playwright', 'uv'):
    assert importlib.util.find_spec(name) is None, name
assert shutil.which('uv') is None
assert shutil.which('uvx') is None
assert not Path('/run/secrets/proxy_ca').exists()
assert not Path('/build').exists()
"""
    sandbox.docker("exec", sandbox.app, "python", "-c", code)
    logs = sandbox.docker("logs", sandbox.app)
    assert "synthetic-session" not in logs.stdout + logs.stderr


def test_stop_start_restart_and_recreate_keep_synthetic_data(
    sandbox: DockerSandbox,
) -> None:
    write_marker = (
        "from pathlib import Path; "
        "Path('/data/synthetic-marker.txt').write_text('synthetic persistence check')"
    )
    read_marker = (
        "from pathlib import Path; "
        "assert Path('/data/synthetic-marker.txt').read_text() == "
        "'synthetic persistence check'"
    )
    write_audit = """
from pathlib import Path
from lebensassistent.database.connection import Database, transaction
from lebensassistent.database.audit import append_audit
with Database(Path('/data/lebensassistent.sqlite3')).connect() as connection:
    with transaction(connection):
        append_audit(connection, entity_type='synthetic', entity_id=1,
                     action='create', after={'label': 'synthetic persistence check'})
"""
    read_audit = """
from pathlib import Path
from lebensassistent.database.connection import Database
from lebensassistent.database.migrations import MIGRATIONS
with Database(Path('/data/lebensassistent.sqlite3')).connect() as connection:
    assert connection.execute(
        "SELECT COUNT(*) FROM audit_log WHERE entity_type = 'synthetic'"
    ).fetchone()[0] == 1
    assert connection.execute(
        'SELECT COUNT(*) FROM schema_migrations'
    ).fetchone()[0] == len(MIGRATIONS)
"""
    sandbox.docker(
        "exec", "--user", "1000:1000", sandbox.app, "python", "-c", write_marker
    )
    sandbox.docker(
        "exec", "--user", "1000:1000", sandbox.app, "python", "-c", write_audit
    )
    sandbox.docker("stop", "--time", "10", sandbox.app)
    state = json.loads(sandbox.docker("inspect", sandbox.app).stdout)[0]["State"]
    assert state["Running"] is False
    assert state["OOMKilled"] is False
    assert state["ExitCode"] in (0, 143)
    logs = sandbox.docker("logs", sandbox.app)
    assert "Application shutdown complete" in logs.stdout + logs.stderr

    sandbox.docker("start", sandbox.app)
    sandbox.wait_ready()
    sandbox.docker(
        "exec", "--user", "1000:1000", sandbox.app, "python", "-c", read_marker
    )
    sandbox.docker(
        "exec", "--user", "1000:1000", sandbox.app, "python", "-c", read_audit
    )
    sandbox.docker("restart", "--time", "10", sandbox.app)
    sandbox.wait_ready()
    sandbox.docker(
        "exec", "--user", "1000:1000", sandbox.app, "python", "-c", read_marker
    )
    sandbox.docker(
        "exec", "--user", "1000:1000", sandbox.app, "python", "-c", read_audit
    )
    sandbox.docker("stop", "--time", "10", sandbox.app)
    sandbox.docker("rm", sandbox.app)
    sandbox.start_app()
    sandbox.docker(
        "exec", "--user", "1000:1000", sandbox.app, "python", "-c", read_marker
    )
    sandbox.docker(
        "exec", "--user", "1000:1000", sandbox.app, "python", "-c", read_audit
    )


def test_database_is_private_initialized_and_consistent(sandbox: DockerSandbox) -> None:
    code = """
from pathlib import Path
from lebensassistent.database.connection import Database
from lebensassistent.database.migrations import MIGRATIONS
path = Path('/data/lebensassistent.sqlite3')
assert path.stat().st_mode & 0o777 == 0o600
assert path.stat().st_uid == path.stat().st_gid == 1000
with Database(path).connect() as connection:
    assert connection.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'
    assert connection.execute('PRAGMA foreign_keys').fetchone()[0] == 1
    assert connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert connection.execute('PRAGMA foreign_key_check').fetchall() == []
    row = connection.execute('SELECT MAX(version) FROM schema_migrations').fetchone()
    assert row[0] == len(MIGRATIONS)
    assert connection.execute(
        "SELECT COUNT(*) FROM audit_log WHERE entity_type='synthetic_upgrade'"
    ).fetchone()[0] == 1
    assert connection.execute(
        "SELECT opening_balance_cents FROM accounts "
        "WHERE name='Synthetisches Upgrade-Konto'"
    ).fetchone()[0] == 10000
    assert connection.execute(
        "SELECT kind FROM categories WHERE name='Synthetische Upgrade-Kategorie'"
    ).fetchone()[0] == 'income'
"""
    sandbox.docker("exec", "--user", "1000:1000", sandbox.app, "python", "-c", code)


def test_real_form_writes_and_csrf_failures(sandbox: DockerSandbox) -> None:
    headers = {"X-Ingress-Path": PREFIX}
    page = sandbox.request(sandbox.trusted, "/bereiche/finanzen", headers)
    assert page["status"] == 200
    match = re.search(r'name="csrf_token" value="([^"]+)"', page["body"])
    assert match is not None
    # HA applies Referrer-Policy: no-referrer; browsers then post Origin: null.
    headers = {**headers, "Origin": "null", "Sec-Fetch-Site": "same-origin"}
    form = {
        "csrf_token": match[1],
        "name": "Synthetisches TCP-Konto",
        "account_type": "checking",
        "opening_balance": "-10,01",
        "opening_date": "2026-01-15",
        "notes": "",
    }
    assert (
        sandbox.request(
            sandbox.untrusted,
            "/konten",
            {**headers, "X-Forwarded-For": "172.30.32.2"},
            form,
        )["status"]
        == 403
    )
    assert (
        sandbox.request(
            sandbox.trusted,
            "/konten",
            headers,
            {**form, "csrf_token": "synthetic-wrong"},
        )["status"]
        == 403
    )
    assert (
        sandbox.request(
            sandbox.trusted,
            "/konten",
            {**headers, "Sec-Fetch-Site": "cross-site"},
            form,
        )["status"]
        == 403
    )
    response = sandbox.request(sandbox.trusted, "/konten", headers, form)
    assert response["status"] == 303
    assert response["headers"]["location"].startswith(f"{PREFIX}/bereiche/finanzen")
    category = {
        "csrf_token": match[1],
        "name": "Synthetische TCP-Kategorie",
        "kind": "expense",
        "parent_id": "",
    }
    assert (
        sandbox.request(sandbox.trusted, "/kategorien", headers, category)["status"]
        == 303
    )
    sandbox.docker("restart", "--time", "10", sandbox.app)
    sandbox.wait_ready()
    page = sandbox.request(sandbox.trusted, "/bereiche/finanzen", headers)
    assert "Synthetisches TCP-Konto" in page["body"]
    assert "-10,01 €" in page["body"]
    assert "Synthetische TCP-Kategorie" in page["body"]

    assert sandbox.request(sandbox.trusted, "/konten", headers, form)["status"] == 403
    logs = sandbox.docker("logs", sandbox.app)
    assert "Synthetisches TCP-Konto" not in logs.stdout + logs.stderr
    assert match[1] not in logs.stdout + logs.stderr
    sandbox.docker("stop", "--time", "10", sandbox.app)
    sandbox.docker("rm", sandbox.app)
    sandbox.start_app()
    page = sandbox.request(sandbox.trusted, "/bereiche/finanzen", headers)
    assert "Synthetisches TCP-Konto" in page["body"]
    assert "-10,01 €" in page["body"]
    assert "Synthetische TCP-Kategorie" in page["body"]


def test_postings_and_balances_survive_recreation(sandbox: DockerSandbox) -> None:
    headers = {
        "X-Ingress-Path": PREFIX,
        "Origin": "null",
        "Sec-Fetch-Site": "same-origin",
    }
    page = sandbox.request(sandbox.trusted, "/bereiche/finanzen", headers)
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page["body"])[1]
    submission = re.search(r'name="submission_id" value="([^"]+)"', page["body"])[1]
    # The fixture seeded this account/category at schema 2, before app startup.
    form = {
        "csrf_token": csrf,
        "submission_id": submission,
        "account_id": "1",
        "category_id": "1",
        "kind": "income",
        "amount": "0,01",
        "booked_date": "2026-01-15",
        "description": "Synthetische TCP-Buchung",
    }
    assert (
        sandbox.request(
            sandbox.untrusted,
            "/buchungen",
            {**headers, "X-Forwarded-For": "172.30.32.2"},
            form,
        )["status"]
        == 403
    )
    assert (
        sandbox.request(
            sandbox.trusted,
            "/buchungen",
            headers,
            {**form, "csrf_token": "synthetic-wrong"},
        )["status"]
        == 403
    )
    for _ in range(2):
        assert (
            sandbox.request(sandbox.trusted, "/buchungen", headers, form)["status"]
            == 303
        )
    assert (
        sandbox.request(
            sandbox.trusted, "/buchungen", headers, {**form, "amount": "9,99"}
        )["status"]
        == 409
    )
    check = """
from pathlib import Path
from datetime import date
from lebensassistent.database.connection import Database
from lebensassistent.services.ledger import LedgerService
database = Database(Path('/data/lebensassistent.sqlite3'))
assert LedgerService(database).balance(1, date(2026, 1, 15)) == 10001
with database.connect() as connection:
    assert connection.execute('SELECT COUNT(*) FROM transactions').fetchone()[0] == 1
    assert connection.execute(
        'SELECT COUNT(*) FROM transaction_splits').fetchone()[0] == 1
    assert connection.execute(
        "SELECT COUNT(*) FROM audit_log WHERE entity_type='transactions'"
    ).fetchone()[0] == 1
"""
    for recreate in (False, True):
        if recreate:
            sandbox.docker("stop", "--time", "10", sandbox.app)
            sandbox.docker("rm", sandbox.app)
            sandbox.start_app()
        else:
            sandbox.docker("restart", "--time", "10", sandbox.app)
            sandbox.wait_ready()
        sandbox.docker(
            "exec", "--user", "1000:1000", sandbox.app, "python", "-c", check
        )
        page = sandbox.request(sandbox.trusted, "/bereiche/finanzen", headers)
        assert "Synthetische TCP-Buchung" in page["body"]
        assert "100,01 €" in page["body"]
    logs = sandbox.docker("logs", sandbox.app)
    for private in (csrf, submission, "Synthetische TCP-Buchung"):
        assert private not in logs.stdout + logs.stderr
