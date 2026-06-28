"""API tests for math proof routes."""

from fastapi.testclient import TestClient

from polomni.api import create_app


def test_math_equations() -> None:
    client = TestClient(create_app())
    r = client.get("/math/equations")
    assert r.status_code == 200
    assert len(r.json()["equations"]) >= 12


def test_math_prove() -> None:
    client = TestClient(create_app())
    r = client.post("/math/prove")
    assert r.status_code == 200
    data = r.json()
    assert data["all_passed"] is True
    assert len(data["results"]) >= 12
