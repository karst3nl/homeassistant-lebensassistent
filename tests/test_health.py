"""API-Vertrag des zustandslosen Health-Checks mit synthetischen Anfragen."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from lebensassistent.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_health_returns_ok_json(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok"}


def test_health_rejects_post(client: TestClient) -> None:
    response = client.post("/health", json={"status": "changed"})

    assert response.status_code == 405
    assert response.json() == {"detail": "Method Not Allowed"}
    assert client.get("/health").json() == {"status": "ok"}


def test_unknown_path_returns_not_found(client: TestClient) -> None:
    response = client.get("/not-a-real-route")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
