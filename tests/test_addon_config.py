"""Sicherheitsgrenzen der HA-Konfiguration unabhängig von einem Supervisor."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_addon_has_ingress_and_no_public_or_privileged_access() -> None:
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    assert config["ingress"] is True
    assert config["ingress_port"] == 8099
    assert config["panel_admin"] is True
    assert "ports" not in config
    assert "webui" not in config
    assert not config.get("map")
    assert not config.get("privileged")
    for flag in (
        "host_network",
        "host_pid",
        "host_dbus",
        "host_uts",
        "full_access",
        "hassio_api",
        "homeassistant_api",
        "auth_api",
        "docker_api",
        "uart",
        "usb",
        "gpio",
        "udev",
        "video",
        "audio",
    ):
        assert not config.get(flag), flag
    assert config.get("apparmor", True) is True
    assert not config.get("devices")


def test_addon_is_experimental_and_builds_from_alpha_sources() -> None:
    config = yaml.safe_load((ROOT / "config.yaml").read_text())
    repository = yaml.safe_load((ROOT / "repository.yaml").read_text())
    assert config["stage"] == "experimental"
    assert config["boot"] == "manual"
    assert set(config["arch"]) == {"amd64", "aarch64"}
    assert "image" not in config
    assert config["options"] == config["schema"] == {}
    assert config["url"].endswith("/tree/alpha")
    assert repository["url"].endswith("/tree/alpha")
    assert (ROOT / "Dockerfile").is_file()
