"""Isolierte Docker-Prüfung ohne HA-Installation oder veröffentlichte Ports."""

import json
import os
import subprocess
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "/api/hassio_ingress/synthetic-session"
HTTP_CLIENT = """
import json, sys
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from urllib.parse import urlencode
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None
opener = build_opener(ProxyHandler({}), NoRedirect())
try:
    form = json.loads(sys.argv[3])
    body = urlencode(form).encode() if form is not None else None
    request = Request(sys.argv[1], data=body, headers=json.loads(sys.argv[2]))
    response = opener.open(request, timeout=5)
except HTTPError as error:
    response = error
print(json.dumps({"status": response.code, "headers": dict(response.headers),
                  "body": response.read().decode()}))
"""


class DockerSandbox:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.name = f"lebensassistent-test-{uuid.uuid4().hex[:10]}"
        self.image = f"{self.name}:local"
        self.app = f"{self.name}-app"
        self.trusted = f"{self.name}-trusted"
        self.untrusted = f"{self.name}-untrusted"
        self.volume = f"{self.name}-data"
        self.network = self.name
        self.environment = os.environ.copy()
        for key in (
            "DOCKER_HOST",
            "DOCKER_CONTEXT",
            "DOCKER_TLS",
            "DOCKER_TLS_VERIFY",
            "DOCKER_CERT_PATH",
        ):
            self.environment.pop(key, None)
        self.command = [
            "docker",
            "--host",
            os.environ.get(
                "LEBENSASSISTENT_DOCKER_HOST", "unix:///var/run/docker.sock"
            ),
        ]

    def docker(
        self, *args: str, check: bool = True, timeout: int = 60
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*self.command, *args],
            cwd=ROOT,
            env=self.environment,
            capture_output=True,
            text=True,
            check=check,
            timeout=timeout,
        )

    def build(self) -> None:
        args = ["build", "--progress=plain", "-t", self.image]
        ca_file = os.environ.get("LEBENSASSISTENT_BUILD_CA_FILE")
        if ca_file:
            dockerfile = self.directory / "Dockerfile"
            dockerfile.write_text(
                (ROOT / "Dockerfile")
                .read_text()
                .replace(
                    "RUN uv sync",
                    "RUN --mount=type=secret,id=proxy_ca,required=true "
                    "SSL_CERT_FILE=/run/secrets/proxy_ca uv sync",
                )
            )
            args.extend(
                ["-f", str(dockerfile), "--secret", f"id=proxy_ca,src={ca_file}"]
            )
        result = self.docker(*args, ".", check=False, timeout=300)
        (self.directory / "build.log").write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stderr[-4000:]

    def start_app(self) -> None:
        started = self.docker(
            "run",
            "-d",
            "--name",
            self.app,
            "--network",
            self.network,
            "--ip",
            "172.30.32.3",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,nosuid,noexec,size=16m",
            "--security-opt",
            "no-new-privileges:true",
            "--cap-drop",
            "ALL",
            "--cap-add",
            "CHOWN",
            "--cap-add",
            "FOWNER",
            "--cap-add",
            "SETUID",
            "--cap-add",
            "SETGID",
            "--mount",
            f"type=volume,src={self.volume},dst=/data",
            self.image,
            check=False,
        )
        assert started.returncode == 0, started.stderr
        self.wait_ready()

    def request(
        self,
        peer: str,
        path: str,
        headers: dict[str, str] | None = None,
        form: dict[str, str] | None = None,
    ) -> dict:
        result = self.docker(
            "exec",
            peer,
            "python",
            "-c",
            HTTP_CLIENT,
            f"http://{self.app}:8099{path}",
            json.dumps(headers or {}),
            json.dumps(form),
        )
        return json.loads(result.stdout)

    def wait_ready(self) -> None:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                response = self.request(
                    self.trusted, "/health", {"X-Ingress-Path": PREFIX}
                )
                if response["status"] == 200:
                    return
            except subprocess.CalledProcessError:
                pass
            time.sleep(0.1)
        pytest.fail(self.docker("logs", self.app, check=False).stderr)

    def cleanup(self) -> None:
        for name in (self.app, self.trusted, self.untrusted):
            result = self.docker("logs", name, check=False)
            (self.directory / f"{name}.log").write_text(result.stdout + result.stderr)
            self.docker("rm", "-f", name, check=False)
        self.docker("volume", "rm", self.volume, check=False)
        self.docker("network", "rm", self.network, check=False)
        self.docker("image", "rm", self.image, check=False)


@pytest.fixture(scope="session")
def sandbox(tmp_path_factory: pytest.TempPathFactory) -> Iterator[DockerSandbox]:
    sandbox = DockerSandbox(tmp_path_factory.mktemp("docker"))
    try:
        sandbox.build()
        sandbox.docker(
            "network",
            "create",
            "--internal",
            "--subnet",
            "172.30.32.0/24",
            sandbox.network,
        )
        sandbox.docker("volume", "create", sandbox.volume)
        seed = """
from pathlib import Path
from lebensassistent.integrations.homeassistant.runtime import (
    DATA_DIR, prepare_data_directory, drop_privileges)
from lebensassistent.database.connection import Database, transaction
from lebensassistent.database.migrations import MIGRATIONS, migrate
from lebensassistent.database.audit import append_audit
from lebensassistent.services.catalog import AccountInput, CatalogService, CategoryInput
import os
os.umask(0o077)
prepare_data_directory(DATA_DIR)
drop_privileges()
database = Database(Path('/data/lebensassistent.sqlite3'))
migrate(database, MIGRATIONS[:2])
catalog = CatalogService(database)
catalog.create_account(AccountInput(name='Synthetisches Upgrade-Konto',
    account_type='checking', opening_balance_cents=10000, opening_date='2026-01-01'))
catalog.create_category(CategoryInput(
    name='Synthetische Upgrade-Kategorie', kind='income'))
with database.connect() as connection, transaction(connection):
    append_audit(connection, entity_type='synthetic_upgrade', entity_id=1,
                 action='test', after={'label': 'synthetic prior audit'})
"""
        sandbox.docker(
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--mount",
            f"type=volume,src={sandbox.volume},dst=/data",
            sandbox.image,
            "python",
            "-c",
            seed,
        )
        for name, address in (
            (sandbox.trusted, "172.30.32.2"),
            (sandbox.untrusted, "172.30.32.4"),
        ):
            sandbox.docker(
                "run",
                "-d",
                "--name",
                name,
                "--network",
                sandbox.network,
                "--ip",
                address,
                "--read-only",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges:true",
                sandbox.image,
                "python",
                "-c",
                "import time; time.sleep(900)",
            )
        sandbox.start_app()
        yield sandbox
    finally:
        sandbox.cleanup()
