"""Tests for API metrics and dashboard."""

from fastapi.testclient import TestClient

from polomni.api import create_app


def test_metrics_endpoint() -> None:
    client = TestClient(create_app())
    r = client.get("/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "uptime_seconds" in data
    assert "cache_product_count" in data


def test_dashboard_html() -> None:
    client = TestClient(create_app())
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "Polomni Lab Dashboard" in r.text


def test_frontend_spa_assets() -> None:
    """Built JS/CSS must be served under /app/assets (Vite base path)."""
    import pathlib
    dist = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if not dist.is_dir() or not (dist / "index.html").is_file():
        __import__("pytest").skip("frontend not built")
    client = TestClient(create_app())
    r = client.get("/app")
    assert r.status_code == 200
    assert "Polomni Multiverse Frontend" in r.text
    assets = dist / "assets"
    if not assets.is_dir():
        return
    js = next(assets.glob("index-*.js"), None)
    if js is None:
        return
    asset = client.get(f"/app/assets/{js.name}")
    assert asset.status_code == 200
    assert "javascript" in asset.headers.get("content-type", "")
