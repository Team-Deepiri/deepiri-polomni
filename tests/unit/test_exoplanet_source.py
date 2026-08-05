"""Unit tests for the NASA Exoplanet Archive world-atlas source."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.observatory.pipeline.sources.exoplanets import (
    alignment_decomposition,
    alignment_tensor,
    angular_separation_deg,
    dipole_bootstrap,
    exoplanet_density_map,
    footprint_permuted_density_map,
    galactic_pole_vector,
    kepler_excision_scan,
    load_exoplanet_catalog,
    method_alignment_scan,
    method_dipole_scan,
    radec_to_sky_coords,
    reference_alignment_table,
    reference_directions,
    sky_occupancy_counts,
    spectrum_null_percentiles,
    world_dipole,
    world_power_spectrum,
    world_vectors,
)

FIXTURE_CSV = """pl_name,hostname,ra,dec,pl_orbper,pl_rade,pl_bmassj,st_teff,pl_eqt,pl_insol,disc_year,discoverymethod
Kepler-1 b,Kepler-1,290.0,50.0,3.2,14.6,0.66,5647.0,1460.0,2.1,2010,Transit
Kepler-2 b,Kepler-2,291.0,51.0,4.1,8.9,,5582.0,,,2016,Transit
Kepler-3 b,Kepler-3,292.0,52.0,2.3,2.6,,5180.0,,,2014,Transit
RV-1 b,RV-1,180.0,20.0,10.0,1.0,0.5,5800.0,,,2012,Radial Velocity
RV-2 b,RV-2,190.0,-20.0,20.0,1.2,1.0,6000.0,,,2015,Radial Velocity
ML-1 b,ML-1,266.4,-29.0,300.0,2.0,3.0,4500.0,,,2018,Microlensing
ML-2 b,ML-2,266.5,-29.2,400.0,1.8,4.0,4600.0,,,2019,Microlensing
Bad-row b,Bad,NOTNUM,55.0,,,,
"""


@pytest.fixture
def catalog(tmp_path):
    path = tmp_path / "ps.csv"
    path.write_text(FIXTURE_CSV)
    return load_exoplanet_catalog(path)


def test_parse_catalog(catalog) -> None:
    assert len(catalog) == 7
    assert catalog.names[0] == "Kepler-1 b"
    assert catalog.hosts[1] == "Kepler-2"
    assert catalog.ra[6] == pytest.approx(266.5)
    # NaN sentinels for missing numeric fields (eq_temp/insol empty for most rows)
    assert np.isnan(catalog.eq_temp[2])
    assert np.isnan(catalog.insol_flux[3])


def test_parse_skips_bad_ra(catalog) -> None:
    # The row with invalid RA is dropped
    assert "Bad-row b" not in catalog.names.tolist()


def test_radec_to_sky_coords_units() -> None:
    x, y, z = radec_to_sky_coords(np.array([0.0]), np.array([0.0]))
    assert np.isclose(np.linalg.norm([x[0], y[0], z[0]]), 1.0)
    x, y, z = radec_to_sky_coords(np.array([0.0]), np.array([90.0]))
    assert np.isclose(z[0], 1.0)


def test_sky_occupancy_counts(catalog) -> None:
    n, occ, frac = sky_occupancy_counts(catalog, 16)
    assert n == 7
    assert occ >= 1
    assert 0.0 < frac <= 1.0


def test_density_map_normalized(catalog) -> None:
    dmap, used, n_good = exoplanet_density_map(catalog, 16)
    assert n_good == 7
    assert len(used) == len(set(used))
    assert dmap.max() == pytest.approx(1.0)
    assert dmap.min() >= 0.0
    assert dmap.size == 12 * 16 * 16


def test_alignment_tensor_trace_invariant(catalog) -> None:
    vecs, good = world_vectors(catalog)
    q = alignment_tensor(vecs)
    assert np.isclose(np.trace(q), 1.0, atol=1e-12)
    assert np.allclose(q, q.T)


def test_alignment_decomposition_structure(catalog) -> None:
    dec = alignment_decomposition(catalog)
    assert dec["n_worlds"] == 7
    assert dec["trace"] == pytest.approx(1.0, abs=1e-12)
    evals = dec["eigenvalues"]
    assert evals[0] >= evals[1] >= evals[2]
    assert np.isclose(sum(evals), 1.0, atol=1e-12)
    assert dec["lam1_minus_isotropic"] == pytest.approx(evals[0] - 1 / 3, abs=1e-9)
    assert dec["order_parameter_s"] == pytest.approx(0.5 * (3 * evals[0] - 1), abs=1e-9)


def test_method_alignment_scan(catalog) -> None:
    methods = method_alignment_scan(catalog, min_worlds=2)
    assert "Transit" in methods
    assert "Microlensing" in methods
    assert methods["Transit"]["n_worlds"] == 3
    assert methods["Microlensing"]["order_parameter_s"] >= 0.0


def test_footprint_permuted_preserves_mask(catalog, tmp_path) -> None:
    rng = np.random.default_rng(0)
    dmap, used, _ = exoplanet_density_map(catalog, 16)
    for _ in range(3):
        null = footprint_permuted_density_map(catalog, 16, rng)
        # Null is a permutation of the occupied-pixel values: same multiset
        np.testing.assert_allclose(np.sort(null[used]), np.sort(dmap[used]))
        # Zero everywhere outside the mask
        np.testing.assert_allclose(null[~np.isin(np.arange(dmap.size), used)], 0.0)


def test_angular_separation_deg() -> None:
    assert angular_separation_deg([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(0.0)
    assert angular_separation_deg([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]) == pytest.approx(90.0)
    # antiparallel axes are the same great circle → 0
    assert angular_separation_deg([1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]) == pytest.approx(0.0)


def test_galactic_pole_vector_unit() -> None:
    g = galactic_pole_vector()
    assert np.isclose(np.linalg.norm(g), 1.0)


def test_world_dipole_magnitude_bounds(catalog) -> None:
    vecs, good = world_vectors(catalog)
    d, mag = world_dipole(vecs)
    assert np.isclose(np.linalg.norm(d), 1.0)
    assert 0.0 <= mag <= 1.0
    # Two mirrored microlensing worlds pull the dipole to ~0 near their midpoint
    vecs_antipodal = np.array([[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]])
    _, mag_anti = world_dipole(vecs_antipodal)
    assert mag_anti < 1e-12


def test_dipole_bootstrap_returns_cone(catalog) -> None:
    boot = dipole_bootstrap(catalog, n_boot=50, seed=1)
    assert boot["n_boot"] == 50
    assert boot["sigma68_deg"] >= 0.0
    assert boot["median_deg"] >= 0.0
    assert len(boot["directions"]) == 50
    assert len(boot["observed_dipole"]) == 3
    assert boot["n_units"] == 7
    assert boot["per_host"] is False


def test_dipole_bootstrap_per_host(catalog) -> None:
    boot = dipole_bootstrap(catalog, n_boot=50, seed=1, per_host=True)
    assert boot["per_host"] is True
    assert boot["n_units"] == 7
    assert boot["sigma68_deg"] >= 0.0


def test_kepler_excision_scan_collapses_dipole(catalog) -> None:
    ex = kepler_excision_scan(catalog, radii_deg=(1.0, 5.0, 8.0))
    assert ex["n_worlds_full"] == 7
    assert ex["full_magnitude"] > 0.0
    assert len(ex["rows"]) == 3
    assert ex["rows"][-1]["n_worlds"] < 7
    for row in ex["rows"]:
        assert row["magnitude"] >= 0.0
        assert "kepler_field_center" in row["references"]
        assert row["isotropic_expectation"] > 0.0


def test_reference_directions_are_unit() -> None:
    refs = reference_directions()
    assert set(refs) == {
        "CMB_dipole_apex",
        "ecliptic_north_pole",
        "kepler_field_center",
        "galactic_north_pole",
    }
    for v in refs.values():
        assert np.isclose(np.linalg.norm(v), 1.0)


def test_reference_alignment_table_structure(catalog) -> None:
    vecs, _ = world_vectors(catalog)
    d, _ = world_dipole(vecs)
    tab = reference_alignment_table(d)
    assert set(tab) == {
        "CMB_dipole_apex",
        "ecliptic_north_pole",
        "kepler_field_center",
        "galactic_north_pole",
    }
    for info in tab.values():
        assert 0.0 <= info["separation_deg"] <= 90.0


def test_method_dipole_scan(catalog) -> None:
    scan = method_dipole_scan(catalog, min_worlds=2, n_boot=30)
    assert "Transit" in scan
    assert "Microlensing" in scan
    assert scan["Microlensing"]["magnitude"] > 0.9
    assert scan["Microlensing"]["sigma68_deg"] < 10.0
    refs = scan["Transit"]["references"]
    assert "kepler_field_center" in refs


def test_world_power_spectrum_shape_and_mask(catalog) -> None:
    spec = world_power_spectrum(catalog, 16)
    assert spec["nside"] == 16
    assert spec["lmax"] == 3 * 16 - 1
    assert len(spec["ell"]) == 48
    assert len(spec["pseudo"]) == 48
    assert len(spec["masked"]) == 48
    assert spec["pseudo"][0] >= 0.0
    assert spec["n_occupied_pixels"] >= 1
    assert 0.0 < spec["occupancy_fraction"] <= 1.0


def test_spectrum_null_returns_band_and_z(catalog) -> None:
    nulls = spectrum_null_percentiles(catalog, 16, n_null=30)
    assert nulls["n_null"] == 30
    assert nulls["n_worlds"] == 7
    assert len(nulls["p16"]) == 48
    assert len(nulls["p50"]) == 48
    assert len(nulls["p84"]) == 48
    assert len(nulls["z_score"]) == 48
    assert len(nulls["p_value"]) == 48
    # Null band is positive and z-scores are finite everywhere
    assert float(nulls["p50"][0]) > 0.0
    assert all(np.isfinite(v) for v in nulls["z_score"])
    assert all(0.0 <= v <= 1.0 for v in nulls["p_value"])
