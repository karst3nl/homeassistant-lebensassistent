"""Statische Oberfläche und synthetischer Ingress-Mount ohne HA-System."""

from collections.abc import Iterator
from html.parser import HTMLParser

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from lebensassistent.main import create_app


class PageLinks(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__()
        self.stylesheets: list[str] = []
        self.links: list[str] = []
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        href = values.get("href")
        if href and tag == "a":
            self.links.append(href)
        if href and tag == "link" and values.get("rel") == "stylesheet":
            self.stylesheets.append(href)


@pytest.fixture(params=["", "/synthetic-ingress"])
def ui_client(request: pytest.FixtureRequest) -> Iterator[tuple[TestClient, str]]:
    prefix = request.param
    app = create_app()
    if prefix:
        parent = FastAPI()
        parent.mount(prefix, app)
        app = parent
    with TestClient(app) as client:
        yield client, prefix


def test_home_and_navigation(ui_client: tuple[TestClient, str]) -> None:
    client, prefix = ui_client
    response = client.get(f"{prefix}/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<html lang="de">' in response.text
    assert 'name="viewport"' in response.text
    links = PageLinks(response.text)
    destinations = {href for href in links.links if not href.startswith("#")}
    assert len(destinations) == 8
    for href in destinations:
        assert href.startswith(f"{prefix}/")
        assert client.get(href).status_code == 200


def test_local_assets_resolve(ui_client: tuple[TestClient, str]) -> None:
    client, prefix = ui_client
    links = PageLinks(client.get(f"{prefix}/").text)

    assert links.stylesheets
    for href in links.stylesheets:
        assert href.startswith(f"{prefix}/static/")
        response = client.get(href)
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/css")


@pytest.mark.parametrize("path", ["/unknown", "/bereiche/unknown"])
def test_browser_404_and_return_link(
    ui_client: tuple[TestClient, str], path: str
) -> None:
    client, prefix = ui_client
    response = client.get(f"{prefix}{path}", headers={"Accept": "text/html"})

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "Seite nicht gefunden" in response.text
    assert f"{prefix}/" in PageLinks(response.text).links


def test_html_405_preserves_status_and_allow(ui_client: tuple[TestClient, str]) -> None:
    client, prefix = ui_client
    response = client.post(f"{prefix}/", headers={"Accept": "text/html"})

    assert response.status_code == 405
    assert response.headers["allow"] == "GET"
    assert "Anfrage nicht unterstützt" in response.text


@pytest.mark.parametrize("path", ["/static/missing.css", "/static/%2e%2e/main.py"])
def test_missing_or_private_asset_is_not_served(
    ui_client: tuple[TestClient, str], path: str
) -> None:
    client, prefix = ui_client
    assert client.get(f"{prefix}{path}").status_code == 404


def test_untrusted_prefix_headers_are_ignored() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/",
            headers={
                "X-Ingress-Path": "https://example.invalid/injected",
                "X-Forwarded-Prefix": "/injected",
            },
        )
    links = PageLinks(response.text)
    assert response.status_code == 200
    assert links.stylesheets == ["/static/styles.css"]
    assert "injected" not in response.text


def test_mount_adds_trailing_slash() -> None:
    parent = FastAPI()
    parent.mount("/synthetic-ingress", create_app())
    with TestClient(parent) as client:
        response = client.get("/synthetic-ingress", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"].endswith("/synthetic-ingress/")


def test_health_keeps_json_for_browser_requests(
    ui_client: tuple[TestClient, str],
) -> None:
    client, prefix = ui_client
    response = client.post(f"{prefix}/health", headers={"Accept": "text/html"})
    assert response.status_code == 405
    assert response.json() == {"detail": "Method Not Allowed"}


def test_sibling_mount_does_not_steal_local_links() -> None:
    parent = FastAPI()
    parent.mount("/other-mount", create_app())
    parent.mount("/", create_app())
    with TestClient(parent) as client:
        response = client.get("/unknown", headers={"Accept": "text/html"})
    assert response.status_code == 404
    links = PageLinks(response.text)
    assert "/" in links.links
    assert links.stylesheets == ["/static/styles.css"]
    assert all(not href.startswith("/other-mount") for href in links.links)


def test_root_path_with_stripped_request_path() -> None:
    with TestClient(create_app(), root_path="/synthetic-ingress") as client:
        response = client.get("/")
        links = PageLinks(response.text)
        assert links.stylesheets == ["/synthetic-ingress/static/styles.css"]
        assert client.get(links.stylesheets[0]).status_code == 200
        response = client.post("/health", headers={"Accept": "text/html"})
        assert response.status_code == 405
        assert response.json() == {"detail": "Method Not Allowed"}


def test_missing_asset_stays_json_for_browser_requests(
    ui_client: tuple[TestClient, str],
) -> None:
    client, prefix = ui_client
    response = client.get(
        f"{prefix}/static/missing.css", headers={"Accept": "text/html"}
    )
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"detail": "Not Found"}
