"""Ingress-Vertrauenskette ausschließlich mit synthetischen Netzwerkdaten."""

import pytest
from fastapi.testclient import TestClient

from lebensassistent.integrations.homeassistant.ingress import create_addon_app

PREFIX = "/api/hassio_ingress/synthetic-session"
TRUSTED_PEER = ("172.30.32.2", 12345)


@pytest.mark.parametrize("peer", ["127.0.0.1", "192.0.2.10", "172.30.32.3", "::1"])
@pytest.mark.parametrize("path", ["/", "/health", "/static/styles.css"])
def test_direct_access_cannot_spoof_ingress(peer: str, path: str) -> None:
    with TestClient(create_addon_app(), client=(peer, 12345)) as client:
        response = client.get(
            path,
            headers={
                "X-Ingress-Path": PREFIX,
                "X-Forwarded-For": TRUSTED_PEER[0],
                "X-Remote-User-Id": "synthetic-user",
            },
        )
    assert response.status_code == 403
    assert response.json() == {"detail": "Forbidden"}


@pytest.mark.parametrize(
    "headers",
    [
        [],
        [("X-Ingress-Path", "")],
        [("X-Ingress-Path", "/")],
        [("X-Ingress-Path", "https://example.invalid/path")],
        [("X-Ingress-Path", "//example.invalid/path")],
        [("X-Ingress-Path", f"{PREFIX}/")],
        [("X-Ingress-Path", f"{PREFIX}/../other")],
        [("X-Ingress-Path", f"{PREFIX}%2fother")],
        [("X-Ingress-Path", f"{PREFIX}?query=value")],
        [("X-Ingress-Path", PREFIX), ("X-Ingress-Path", PREFIX)],
    ],
)
def test_trusted_peer_still_needs_one_valid_prefix(
    headers: list[tuple[str, str]],
) -> None:
    with TestClient(create_addon_app(), client=TRUSTED_PEER) as client:
        response = client.get("/", headers=headers)
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid ingress path"}


@pytest.mark.parametrize(
    ("path", "status"),
    [("/", 200), ("/health", 200), ("/static/styles.css", 200), ("/missing", 404)],
)
def test_authorized_requests_and_prefix_links(path: str, status: int) -> None:
    with TestClient(create_addon_app(), client=TRUSTED_PEER) as client:
        response = client.get(
            path, headers={"X-Ingress-Path": PREFIX, "Accept": "text/html"}
        )
    assert response.status_code == status
    if path in ("/", "/missing"):
        assert f'href="{PREFIX}/static/styles.css"' in response.text
        assert f'href="{PREFIX}/"' in response.text
    elif path == "/health":
        assert response.json() == {"status": "ok"}


def test_ingress_redirect_is_relative_and_preserves_prefix_and_query() -> None:
    with TestClient(create_addon_app(), client=TRUSTED_PEER) as client:
        response = client.get(
            "/bereiche/finanzen/?synthetic=value",
            headers={"X-Ingress-Path": PREFIX, "Host": "example.invalid"},
            follow_redirects=False,
        )
    assert response.status_code == 307
    assert response.headers["location"] == f"{PREFIX}/bereiche/finanzen?synthetic=value"


def test_each_request_uses_its_own_prefix() -> None:
    with TestClient(create_addon_app(), client=TRUSTED_PEER) as client:
        for token in ("synthetic-first", "synthetic-second"):
            prefix = f"/api/hassio_ingress/{token}"
            response = client.get("/", headers={"X-Ingress-Path": prefix})
            assert f'href="{prefix}/static/styles.css"' in response.text
            other = (
                "synthetic-second" if token == "synthetic-first" else "synthetic-first"
            )
            assert other not in response.text
