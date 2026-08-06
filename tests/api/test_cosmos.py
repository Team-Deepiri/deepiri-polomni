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


def test_cosmos_bubble_search_when_cached() -> None:
    from polomni.observatory.pipeline.cache import DataCache

    if DataCache().resolved_path("planck_smica_cmb") is None:
        return
    client = TestClient(create_app())
    r = client.get("/cosmos/bubble-search?nside=32&n_null=4&n_null_rank1=4")
    assert r.status_code == 200
    data = r.json()
    assert data["instrument"].startswith("bubble-collision")
    assert data["p_value"] >= 0.0
    assert "strongest_circle" in data
    assert "harmonic_axis" in data
    assert "verdict" in data


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


def test_cosmos_sky_raster_when_cached() -> None:
    if not cache_ready():
        return
    client = TestClient(create_app())
    r = client.get("/cosmos/sky/raster?nside=32&width=256&height=128")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_cosmos_sky_overlays_when_cached() -> None:
    if not cache_ready():
        return
    client = TestClient(create_app())
    r = client.get("/cosmos/sky/overlays?nside=32")
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 2
    assert "metadata" in data


def test_cosmos_sky_world_when_cached() -> None:
    if not cache_ready():
        return
    client = TestClient(create_app())
    r = client.get("/cosmos/sky/world?nside=32&frame=galactic")
    assert r.status_code == 200
    data = r.json()
    assert "surveys" in data
    assert "dss2" in data["surveys"]
    assert "rble" in data
    assert "gw_events" in data
    assert len(data["rble"]["scar_ring"]) > 0


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
