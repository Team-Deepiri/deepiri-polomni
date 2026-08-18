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


def test_p1_blind_run_conflicts_when_canonical_is_sealed(
    monkeypatch,
    tmp_path,
) -> None:
    from polomni.observatory.studies.results import publish_result

    monkeypatch.chdir(tmp_path)
    publish_result(
        {"mode": "holdout_blind", "blind": True},
        mode="holdout_blind",
    )

    client = TestClient(create_app())
    response = client.post("/study/p1/run?blind=true&calibration=false")

    assert response.status_code == 409
    assert "operator action" in response.json()["detail"]
