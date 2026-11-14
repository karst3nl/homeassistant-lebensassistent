"""Fester Containerstart mit privatem /data und anschließendem Rechteabwurf."""

import os
import tempfile
from pathlib import Path

import uvicorn

from lebensassistent.integrations.homeassistant.ingress import create_addon_app

DATA_DIR = Path("/data")
APP_UID = 1000
APP_GID = 1000


def prepare_data_directory(directory: Path) -> None:
    if directory.is_symlink():
        raise RuntimeError("Data directory must not be a symlink")
    directory.mkdir(mode=0o700, exist_ok=True)
    if os.geteuid() == 0:
        os.chown(directory, APP_UID, APP_GID)
    directory.chmod(0o700)


def drop_privileges() -> None:
    if os.geteuid() == 0:
        os.setgroups([])
        os.setgid(APP_GID)
        os.setuid(APP_UID)


def verify_writable_data_directory(directory: Path) -> None:
    with tempfile.TemporaryFile(dir=directory) as probe:
        probe.write(b"synthetic write probe")
        probe.flush()


def main() -> None:
    os.umask(0o077)
    prepare_data_directory(DATA_DIR)
    drop_privileges()
    verify_writable_data_directory(DATA_DIR)
    uvicorn.run(
        create_addon_app(),
        host="0.0.0.0",
        port=8099,
        proxy_headers=False,
        access_log=False,
        server_header=False,
    )
