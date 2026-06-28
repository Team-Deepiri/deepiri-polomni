"""REST API route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from polomni.api import create_app
from polomni.observatory.pipeline.catalog import CATALOG


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "polomni-lab"


def test_catalog(client: TestClient) -> None:
    response = client.get("/data/catalog")
    assert response.status_code == 200
    products = response.json()
    assert len(products) == len(CATALOG)
    ids = {p["id"] for p in products}
    assert "wmap_k_band" in ids
    assert "planck_cmb_tt_power" in ids


def test_status(client: TestClient) -> None:
    response = client.get("/data/status")
    assert response.status_code == 200
    statuses = response.json()
    assert isinstance(statuses, list)
    assert len(statuses) >= len(CATALOG)
    for item in statuses:
        assert "product_id" in item
        assert "cached" in item
        if item["cached"]:
            assert item["size_bytes"] is not None
            assert item["size_bytes"] > 0


def test_scan_synthetic(client: TestClient) -> None:
    response = client.post(
        "/observatory/scan",
        json={"synthetic": True, "nside": 32, "nulls": 5},
    )
    assert response.status_code == 200
    data = response.json()
    assert "rble_score" in data
    assert isinstance(data["preferred_axis"], list)
    assert len(data["preferred_axis"]) == 3
    assert "falsification_flags" in data
    assert "metadata" in data
