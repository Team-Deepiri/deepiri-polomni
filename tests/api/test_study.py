"""API tests for study routes."""

from fastapi.testclient import TestClient

from polomni.api.app import create_app


def test_p1_gates_endpoint() -> None:
    client = TestClient(create_app())
    r = client.get("/study/p1/gates")
    assert r.status_code == 200
    data = r.json()
    assert "checks" in data
    assert len(data["checks"]) == 3
