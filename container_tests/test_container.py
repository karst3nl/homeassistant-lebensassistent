"""Reale Container: TCP-Vertrauenskette, Rechte, Lebenszyklus und Testpersistenz."""

import json

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
    sandbox.docker(
        "exec", "--user", "1000:1000", sandbox.app, "python", "-c", write_marker
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
    sandbox.docker("restart", "--time", "10", sandbox.app)
    sandbox.wait_ready()
    sandbox.docker(
        "exec", "--user", "1000:1000", sandbox.app, "python", "-c", read_marker
    )
    sandbox.docker("stop", "--time", "10", sandbox.app)
    sandbox.docker("rm", sandbox.app)
    sandbox.start_app()
    sandbox.docker(
        "exec", "--user", "1000:1000", sandbox.app, "python", "-c", read_marker
    )
