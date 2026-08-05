"""Tests for the World Atlas payload + /cosmos/worlds route."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.catalog import get_product
from polomni.observatory.pipeline.downloader import fetch_product
from polomni.viz.cosmos.worlds import exoplanet_world_payload

FIXTURE_CSV = """pl_name,hostname,ra,dec,pl_orbper,pl_rade,pl_bmassj,st_teff,pl_eqt,pl_insol,disc_year,discoverymethod
Kepler-1 b,Kepler-1,290.0,50.0,3.2,14.6,0.66,5647.0,1460.0,2.1,2010,Transit
Kepler-2 b,Kepler-2,291.0,51.0,4.1,8.9,,5582.0,,,2016,Transit
Kepler-3 b,Kepler-3,292.0,52.0,2.3,2.6,,5180.0,,,2014,Transit
RV-1 b,RV-1,180.0,20.0,10.0,1.0,0.5,5800.0,,,2012,Radial Velocity
RV-2 b,RV-2,190.0,-20.0,20.0,1.2,1.0,6000.0,,,2015,Radial Velocity
ML-1 b,ML-1,266.4,-29.0,300.0,2.0,3.0,4500.0,,,2018,Microlensing
ML-2 b,ML-2,266.5,-29.2,400.0,1.8,4.0,4600.0,,,2019,Microlensing
"""


def _cache_with_fixture(tmp_path) -> DataCache:
    cache = DataCache(root=tmp_path / "cache")
    product = get_product("nasa_exoplanet_ps")
    dest = cache.root / product.id / product.cache_filename()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(FIXTURE_CSV)
    cache.record(product.id, dest, product.url, extra={"fixture": True})
    return cache


def _use_cache_root(monkeypatch, tmp_path) -> DataCache:
    from polomni.observatory.pipeline.config import reset_settings_cache

    cache = _cache_with_fixture(tmp_path)
    monkeypatch.setenv("POLOMNI_DATA_CACHE", str(cache.root))
    reset_settings_cache()
    return cache


def test_world_payload_structure(tmp_path) -> None:
    cache = _cache_with_fixture(tmp_path)
    payload = exoplanet_world_payload(nside=16, n_ensemble=6, min_worlds=2, cache=cache)
    assert payload["ready"] is True
    assert payload["catalog"]["n_worlds"] == 7
    assert payload["scan"]["rble_score"] > 0
    assert len(payload["scan"]["preferred_axis"]) == 3
    assert payload["scan"]["n_ensemble"] == 6
    assert payload["alignment"]["trace"] == pytest.approx(1.0, abs=1e-12)
    assert set(payload["methods"].keys()) >= {"Transit", "Microlensing", "Radial Velocity"}
    assert len(payload["points"]["lon"]) == len(payload["points"]["name"])
    assert "null_sigma_significance" in payload["scan"]
    assert "separation_from_galactic_pole_deg" in payload["scan"]


def test_world_payload_weight_teff(tmp_path) -> None:
    cache = _cache_with_fixture(tmp_path)
    payload = exoplanet_world_payload(nside=16, n_ensemble=4, weight="teff", cache=cache)
    assert payload["weight"] == "teff"
    assert payload["scan"]["rble_score"] > 0


def test_world_route(tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from polomni.api import create_app

    _use_cache_root(monkeypatch, tmp_path)

    client = TestClient(create_app())
    r = client.get("/cosmos/worlds?nside=16&n_ensemble=6")
    assert r.status_code == 200
    data = r.json()
    assert data["catalog"]["n_worlds"] == 7
    assert data["scan"]["n_ensemble"] == 6


def test_world_route_bad_weight(tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from polomni.api import create_app

    _use_cache_root(monkeypatch, tmp_path)
    client = TestClient(create_app())
    r = client.get("/cosmos/worlds?weight=bogus")
    assert r.status_code == 422
