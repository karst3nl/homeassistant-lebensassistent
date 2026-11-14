"""Laufzeitvorbereitung nur in temporären synthetischen Verzeichnissen."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from lebensassistent.integrations.homeassistant import runtime
from lebensassistent.integrations.homeassistant.ingress import IngressMiddleware


def test_data_directory_is_private_and_keeps_existing_content(tmp_path: Path) -> None:
    data_dir = tmp_path / "synthetic-data"
    runtime.prepare_data_directory(data_dir)
    marker = data_dir / "synthetic-marker.txt"
    marker.write_text("synthetic persistence check")
    runtime.prepare_data_directory(data_dir)
    runtime.verify_writable_data_directory(data_dir)

    assert data_dir.stat().st_mode & 0o777 == 0o700
    assert marker.read_text() == "synthetic persistence check"
    assert list(data_dir.iterdir()) == [marker]
    assert runtime.DATA_DIR == Path("/data")


def test_data_directory_cannot_be_a_symlink(tmp_path: Path) -> None:
    target = tmp_path / "synthetic-target"
    target.mkdir()
    link = tmp_path / "synthetic-link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(RuntimeError, match="symlink"):
        runtime.prepare_data_directory(link)


def test_unavailable_data_prevents_startup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "missing-parent" / "synthetic-data"
    monkeypatch.setattr(runtime, "DATA_DIR", directory)
    monkeypatch.setattr(runtime.os, "umask", Mock())
    start_server = Mock()
    monkeypatch.setattr(runtime.uvicorn, "run", start_server)
    with pytest.raises(OSError):
        runtime.main()
    start_server.assert_not_called()


def test_entrypoint_starts_only_protected_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runtime, "DATA_DIR", tmp_path / "synthetic-data")
    monkeypatch.setattr(runtime.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(runtime.os, "umask", Mock())
    start_server = Mock()
    monkeypatch.setattr(runtime.uvicorn, "run", start_server)
    runtime.main()

    args, kwargs = start_server.call_args
    assert isinstance(args[0], IngressMiddleware)
    assert kwargs["host"] == "0.0.0.0"
    assert kwargs["port"] == 8099
    assert kwargs["proxy_headers"] is False
    assert kwargs["access_log"] is False


def test_root_privileges_are_dropped_in_safe_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operations: list[tuple[str, object]] = []
    monkeypatch.setattr(runtime.os, "geteuid", lambda: 0)
    monkeypatch.setattr(
        runtime.os, "setgroups", lambda values: operations.append(("groups", values))
    )
    monkeypatch.setattr(
        runtime.os, "setgid", lambda value: operations.append(("gid", value))
    )
    monkeypatch.setattr(
        runtime.os, "setuid", lambda value: operations.append(("uid", value))
    )
    runtime.drop_privileges()
    assert operations == [("groups", []), ("gid", 1000), ("uid", 1000)]
