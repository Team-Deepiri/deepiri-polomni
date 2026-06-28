"""API tests for cosmos lab routes."""

from fastapi.testclient import TestClient

from polomni.api import create_app
from polomni.math.proofs.real_data import cache_ready


def test_cosmos_snapshot() -> None:
    client = TestClient(create_app())
    r = client.get("/cosmos/snapshot")
    assert r.status_code == 200
    data = r.json()
    assert data["kind"] == "cosmos_snapshot"
    assert "gates" in data
    assert "timestamp" in data


def test_cosmos_verify_status() -> None:
    client = TestClient(create_app())
    r = client.get("/cosmos/verify/status")
    assert r.status_code == 200
    assert "running" in r.json()


def test_cosmos_study() -> None:
    client = TestClient(create_app())
    r = client.get("/cosmos/study")
    assert r.status_code == 200
    assert "gates" in r.json()


def test_cosmos_sky_when_cached() -> None:
    if not cache_ready():
        return
    client = TestClient(create_app())
    r = client.get("/cosmos/sky?nside=32")
    assert r.status_code == 200
    data = r.json()
    assert len(data["lon"]) > 0
    assert "rble_score" in data
    assert "scar_ring" in data


def test_cosmos_compare_when_cached() -> None:
    if not cache_ready():
        return
    client = TestClient(create_app())
    r = client.get("/cosmos/compare?nside=32")
    assert r.status_code == 200
    data = r.json()
    assert "calibration" in data
    assert "holdout" in data
    assert data["calibration"]["sky"]["rble_score"] > 0


def test_cosmos_histogram_when_cached() -> None:
    if not cache_ready():
        return
    client = TestClient(create_app())
    r = client.get("/cosmos/null-histogram?nside=32&n_ensemble=12")
    assert r.status_code == 200
    data = r.json()
    assert "histogram" in data
    assert data["n_ensemble"] == 12
