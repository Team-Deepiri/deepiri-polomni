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
