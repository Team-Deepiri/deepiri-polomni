"""API tests for viz data routes."""

from fastapi.testclient import TestClient

from polomni.api import create_app


def test_viz_district_graph() -> None:
    client = TestClient(create_app())
    r = client.get("/viz/district-graph?choices=3")
    assert r.status_code == 200
    data = r.json()
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0


def test_viz_landscape() -> None:
    client = TestClient(create_app())
    r = client.get("/viz/landscape?grid_size=8")
    assert r.status_code == 200
    assert "z" in r.json()


def test_viz_scar_sphere() -> None:
    client = TestClient(create_app())
    r = client.get("/viz/scar-sphere?nside=16")
    assert r.status_code == 200
    assert "preferred_axis" in r.json()


def test_viz_falsification() -> None:
    client = TestClient(create_app())
    r = client.get("/viz/falsification")
    assert r.status_code == 200
    data = r.json()
    assert "p1" in data and "p2" in data and "p3" in data


def test_viz_physics_loop() -> None:
    client = TestClient(create_app())
    r = client.get("/viz/physics-loop?steps=1&nside=16")
    assert r.status_code == 200
    data = r.json()
    assert "real_axis" in data
    assert "steps" in data
    assert "graph" in data
