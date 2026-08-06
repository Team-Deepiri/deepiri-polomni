"""Tests for the /cosmos/cross-sky route."""

from __future__ import annotations

import json

import pytest

FIXTURE_CSV = (
    "pl_name,hostname,ra,dec,pl_orbper,pl_rade,pl_bmassj,st_teff,"
    "pl_eqt,pl_insol,disc_year,discoverymethod\n"
    "A-1 b,A,290.0,50.0,3.2,1.0,,5600.0,,,,2010,Transit\n"
    "A-2 b,A,291.0,51.0,4.1,1.0,,5500.0,,,,2010,Transit\n"
    "A-3 b,A,292.0,52.0,2.3,1.0,,5400.0,,,,2010,Transit\n"
    "B-1 b,B,10.0,20.0,5.0,1.0,,5800.0,,,,2012,Transit\n"
    "B-2 b,B,11.0,21.0,6.0,1.0,,5900.0,,,,2012,Transit\n"
)

SDSS_FIXTURE = [
    {"ra": 10.0, "dec": 20.0, "z": 0.3, "kind": "galaxy"},
    {"ra": 20.0, "dec": 30.0, "z": 0.4, "kind": "galaxy"},
    {"ra": 30.0, "dec": 40.0, "z": 0.5, "kind": "galaxy"},
    {"ra": 40.0, "dec": 50.0, "z": 0.6, "kind": "galaxy"},
]


def _use_cache_root(monkeypatch, tmp_path):
    from polomni.observatory.pipeline.cache import DataCache
    from polomni.observatory.pipeline.config import reset_settings_cache

    cache = DataCache(root=tmp_path / "cache")
    cache.root.mkdir(parents=True, exist_ok=True)
    (cache.root / "nasa_exoplanet_ps").mkdir(parents=True, exist_ok=True)
    (cache.root / "nasa_exoplanet_ps" / "nasa_exoplanet_ps.csv").write_text(FIXTURE_CSV)
    (cache.root / "sdss_bao_ladder").mkdir(parents=True, exist_ok=True)
    (cache.root / "sdss_bao_ladder" / "sdss_sky_objects.json").write_text(
        json.dumps(SDSS_FIXTURE * 5)
    )
    monkeypatch.setenv("POLOMNI_DATA_CACHE", str(cache.root))
    reset_settings_cache()
    return cache


def test_cross_sky_route(tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from polomni.api import create_app

    _use_cache_root(monkeypatch, tmp_path)
    client = TestClient(create_app())
    r = client.get("/cosmos/cross-sky?min_objects=3")
    assert r.status_code == 200
    data = r.json()
    assert data["n_skies"] == 2
    names = {s["sky"] for s in data["skies"]}
    assert names == {"exoplanets", "sdss_galaxies"}
    for s in data["skies"]:
        assert s["n_objects"] >= 3
        assert "references" in s
    assert len(data["pairwise"]) == 1
    assert data["pairwise"][0]["separation_deg"] >= 0.0


def test_cross_sky_route_rejects_instrument_gw(tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from polomni.api import create_app

    _use_cache_root(monkeypatch, tmp_path)
    from polomni.observatory.pipeline.cache import DataCache

    cache = DataCache()
    gw_dir = cache.root / "gwtc_events"
    gw_dir.mkdir(parents=True, exist_ok=True)
    (gw_dir / "gwtc_events.json").write_text(
        json.dumps(
            {
                "events": [
                    {"name": f"G{i}", "network_axis": [0.884, -0.099, 0.457]}
                    for i in range(5)
                ]
            }
        )
    )
    client = TestClient(create_app())
    r = client.get("/cosmos/cross-sky?min_objects=3")
    assert r.status_code == 200
    data = r.json()
    assert data["n_skies"] == 2
    # GW excluded (instrument geometry), not counted as a sky
    assert "gw_events" not in {s["sky"] for s in data["skies"]}
