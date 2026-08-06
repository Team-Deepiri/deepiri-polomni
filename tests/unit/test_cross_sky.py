"""Unit tests for the cross-sky axis comparison module."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.observatory.pipeline.sources.cross_sky import (
    cross_sky_report,
    load_galaxy_vectors,
    load_gw_vectors,
    sky_dipole_report,
    sky_samples,
)

SDSS_FIXTURE = [
    {"ra": 10.0, "dec": 20.0, "z": 0.3, "kind": "galaxy"},
    {"ra": 20.0, "dec": 30.0, "z": 0.4, "kind": "galaxy"},
    {"ra": 30.0, "dec": 40.0, "z": 0.5, "kind": "galaxy"},
    {"ra": 40.0, "dec": 50.0, "z": 0.6, "kind": "galaxy"},
]

GW_SKY_FIXTURE = [
    {"name": "GW1", "network_axis": [1.0, 0.0, 0.0]},
    {"name": "GW2", "network_axis": [0.0, 1.0, 0.0]},
    {"name": "GW3", "network_axis": [0.0, 0.0, 1.0]},
]

# Degenerate: all events share the detector-triangle normal — not sky direction
GW_INSTRUMENT_FIXTURE = [
    {"name": "G1", "network_axis": [0.884, -0.099, 0.457]},
    {"name": "G2", "network_axis": [0.884, -0.099, 0.457]},
    {"name": "G3", "network_axis": [0.884, -0.099, 0.457]},
]


def test_load_galaxy_vectors_units() -> None:
    v = load_galaxy_vectors(SDSS_FIXTURE)
    assert v.shape == (4, 3)
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0)


def test_load_gw_vectors_accepts_varying_directions() -> None:
    v = load_gw_vectors(GW_SKY_FIXTURE)
    assert v.shape == (3, 3)
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0)


def test_load_gw_vectors_rejects_instrument_geometry() -> None:
    with pytest.raises(ValueError, match="detector geometry"):
        load_gw_vectors(GW_INSTRUMENT_FIXTURE)


def test_sky_dipole_report_structure() -> None:
    from polomni.observatory.pipeline.sources.cross_sky import SkySample

    sample = SkySample(
        name="test_sky",
        vectors=load_galaxy_vectors(SDSS_FIXTURE),
        n_objects=4,
        note="fixture",
    )
    rep = sky_dipole_report(sample)
    assert rep["sky"] == "test_sky"
    assert rep["n_objects"] == 4
    assert len(rep["dipole"]) == 3
    assert rep["magnitude"] >= 0.0
    assert "kepler_field_center" in rep["references"]


def test_cross_sky_report_pairwise(tmp_path, monkeypatch) -> None:
    from polomni.observatory.pipeline.cache import DataCache
    from polomni.observatory.pipeline.config import reset_settings_cache

    cache = DataCache(root=tmp_path / "cache")
    import json

    cache.root.mkdir(parents=True, exist_ok=True)
    (cache.root / "sdss_bao_ladder").mkdir(parents=True, exist_ok=True)
    (cache.root / "sdss_bao_ladder" / "sdss_sky_objects.json").write_text(
        json.dumps(SDSS_FIXTURE * 6)
    )
    (cache.root / "nasa_exoplanet_ps").mkdir(parents=True, exist_ok=True)
    fixture_csv = (
        "pl_name,hostname,ra,dec,pl_orbper,pl_rade,pl_bmassj,st_teff,"
        "pl_eqt,pl_insol,disc_year,discoverymethod\n"
        "A-1 b,A,290.0,50.0,3.2,1.0,,5600.0,,,,2010,Transit\n"
        "A-2 b,A,291.0,51.0,4.1,1.0,,5500.0,,,,2010,Transit\n"
        "A-3 b,A,292.0,52.0,2.3,1.0,,5400.0,,,,2010,Transit\n"
    )
    (cache.root / "nasa_exoplanet_ps" / "nasa_exoplanet_ps.csv").write_text(fixture_csv)

    monkeypatch.setenv("POLOMNI_DATA_CACHE", str(cache.root))
    reset_settings_cache()

    report = cross_sky_report(cache=cache, min_objects=3)
    assert report["n_skies"] == 2
    names = {s["sky"] for s in report["skies"]}
    assert names == {"exoplanets", "sdss_galaxies"}
    assert len(report["pairwise"]) == 1
    pair = report["pairwise"][0]
    assert pair["sky_a"] == "exoplanets"
    assert pair["sky_b"] == "sdss_galaxies"
    assert 0.0 <= pair["separation_deg"] <= 90.0
