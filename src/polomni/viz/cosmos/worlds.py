"""World Atlas — RBLE scan over real NASA Exoplanet Archive sky positions.

Maps the actual sky distribution of confirmed exoplanets to a HEALPix density
map, runs the RBLE geodesic-Radon scar scan over it, and reports two
selection-bias audits that an isotropic null would fake:

1. **Footprint-matched null** — counts are reshuffled *within* the observed
   occupancy mask, preserving the Kepler/TESS survey footprint that already
   breaks isotropy. The reported σ is against this honest null.
2. **Per-method axis audit** — the preferred axis is recomputed per discovery
   method. A genuine scar must persist across methods with different sky
   coverage (Transit ≈ Kepler field vs Radial Velocity ≈ sky-complete).

Theory + invariants: docs/theory/WORLD_ATLAS.md
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.catalog import get_product
from polomni.observatory.pipeline.downloader import fetch_product
from polomni.observatory.pipeline.sources.exoplanets import (
    alignment_decomposition,
    angular_separation_deg,
    dipole_bootstrap,
    exoplanet_density_map,
    footprint_permuted_density_map,
    galactic_pole_vector,
    kepler_excision_scan,
    load_exoplanet_catalog,
    method_alignment_scan,
    method_dipole_scan,
    radec_to_lonlat,
    reference_alignment_table,
    reference_directions,
    sky_occupancy_counts,
    spectrum_null_percentiles,
    world_dipole,
    world_power_spectrum,
    world_vectors,
)
from polomni.observatory.scoring.rble_signature import compute_rble_signature
from polomni.viz.cosmos.helpers import axis_lonlat, great_circle_ring

EXOPLANET_PRODUCT_ID = "nasa_exoplanet_ps"
WorldWeight = Literal["count", "teff", "period"]


def _load_catalog(cache: DataCache | None = None):
    cache = cache or DataCache()
    path = cache.resolved_path(EXOPLANET_PRODUCT_ID)
    if path is None:
        product = get_product(EXOPLANET_PRODUCT_ID)
        result = fetch_product(product, cache, force=False)
        path = result.path
    return load_exoplanet_catalog(path), path


def _world_points(catalog, max_points: int = 1500) -> dict[str, list]:
    good = ~(np.isnan(catalog.ra) | np.isnan(catalog.dec))
    ra = catalog.ra[good]
    dec = catalog.dec[good]
    names = catalog.names[good]
    hosts = catalog.hosts[good]
    period = catalog.period_days[good]
    teff = catalog.st_teff[good]
    radius = catalog.radius_earth[good]
    year = catalog.disc_year[good]
    method = catalog.method[good]
    eqt = catalog.eq_temp[good]

    idx = np.arange(ra.size)
    if ra.size > max_points:
        step = max(1, ra.size // max_points)
        idx = idx[::step]

    def _num(a: np.ndarray, k: int = 2) -> list[float]:
        return [float(np.round(v, k)) if not np.isnan(v) else None for v in a[idx]]

    return {
        "lon": [float(v) for v in ra[idx]],
        "lat": [float(v) for v in dec[idx]],
        "name": [str(v) for v in names[idx]],
        "host": [str(v) for v in hosts[idx]],
        "period_days": _num(period),
        "st_teff": _num(teff),
        "radius_earth": _num(radius),
        "disc_year": _num(year, 0),
        "method": [str(v) for v in method[idx]],
        "eq_temp": _num(eqt),
        "n_worlds": int(ra.size),
    }


def exoplanet_world_payload(
    *,
    nside: int = 32,
    weight: WorldWeight = "count",
    n_ensemble: int = 40,
    n_null: int = 100,
    max_points: int = 1500,
    seed: int = 11,
    min_worlds: int = 50,
    cache: DataCache | None = None,
) -> dict[str, Any]:
    """Full world-atlas payload: density scan, footprint null, axis audit."""
    catalog, path = _load_catalog(cache)

    density, used_pix, n_good = exoplanet_density_map(catalog, nside, weight=weight)
    detection = compute_rble_signature(density, scan_angles=36)
    axis = np.asarray(detection.preferred_axis, dtype=float)

    # Footprint-matched null at the fixed observed axis (fast single integrals).
    rng = np.random.default_rng(seed)
    null_scores = [
        float(
            compute_rble_signature(
                footprint_permuted_density_map(catalog, nside, rng, weight=weight),
                axis,
                scan_angles=1,
            ).rble_score
        )
        for _ in range(n_ensemble)
    ]
    null_mu = float(np.mean(null_scores))
    null_sigma = float(np.std(null_scores))
    null_sigma_signif = (
        float((detection.rble_score - null_mu) / (null_sigma + 1e-12))
        if null_sigma > 0
        else 0.0
    )

    align = alignment_decomposition(catalog)
    methods = method_alignment_scan(catalog, min_worlds=min_worlds)

    galactic_pole = galactic_pole_vector()
    methods = {
        method: {
            **info,
            "separation_from_galactic_pole_deg": float(
                angular_separation_deg(info["preferred_axis"], galactic_pole)
            ),
        }
        for method, info in methods.items()
    }

    # Dipole test: does any world-sample dipole point at a physical rest frame
    # (CMB dipole apex) rather than at a survey artifact (Kepler field)?
    vecs, _good = world_vectors(catalog)
    dipole, dipole_mag = world_dipole(vecs)
    bootstrap = dipole_bootstrap(catalog, n_boot=200)
    bootstrap_per_host = dipole_bootstrap(catalog, n_boot=200, per_host=True)
    dipole_refs = reference_alignment_table(dipole)
    method_dipoles = method_dipole_scan(catalog, min_worlds=min_worlds)
    excision = kepler_excision_scan(catalog)

    # World-sky angular power spectrum: only multipoles clearing the
    # uniform-within-footprint null deserve a physical reading.
    spectrum = world_power_spectrum(catalog, nside, weight=weight)
    spectrum_null = spectrum_null_percentiles(
        catalog, nside, weight=weight, n_null=n_null
    )

    axis_lon, axis_lat = axis_lonlat(axis)
    ring_lon, ring_lat = great_circle_ring(axis)
    n_planets, n_occupied, occ_frac = sky_occupancy_counts(catalog, nside)

    lon, lat = radec_to_lonlat(catalog.ra, catalog.dec)
    points = _world_points(catalog, max_points=max_points)

    return {
        "ready": True,
        "source": EXOPLANET_PRODUCT_ID,
        "cache_path": str(path),
        "nside": nside,
        "weight": weight,
        "catalog": {
            "n_worlds": len(catalog),
            "n_hosts": int(np.unique(catalog.hosts).size),
            "n_planets_sky": n_planets,
            "occupied_pixels": n_occupied,
            "occupancy_fraction": occ_frac,
            "years_range": [
                int(np.nanmin(catalog.disc_year)),
                int(np.nanmax(catalog.disc_year)),
            ],
            "methods": sorted({str(m) for m in catalog.method}),
        },
        "density": {
            "lon": [float(v) for v in lon],
            "lat": [float(v) for v in lat],
            "values": density.tolist(),
            "n_pixels": int(density.size),
            "used_pixels": len(used_pix),
        },
        "scan": {
            "rble_score": float(detection.rble_score),
            "preferred_axis": axis.tolist(),
            "null_mu": null_mu,
            "null_sigma": null_sigma,
            "null_sigma_significance": null_sigma_signif,
            "n_ensemble": n_ensemble,
            "weight": weight,
            "separation_from_galactic_pole_deg": float(
                angular_separation_deg(axis, galactic_pole)
            ),
            "metadata": detection.metadata,
        },
        "axis_marker": {"lon": axis_lon, "lat": axis_lat},
        "scar_ring": {"lon": ring_lon, "lat": ring_lat},
        "alignment": align,
        "dipole": {
            "vector": dipole.tolist(),
            "magnitude": dipole_mag,
            "references": dipole_refs,
            "bootstrap": {
                "n_boot": bootstrap["n_boot"],
                "n_units": bootstrap["n_units"],
                "per_host": bootstrap["per_host"],
                "sigma68_deg": bootstrap["sigma68_deg"],
                "median_deg": bootstrap["median_deg"],
                "observed_dipole": bootstrap["observed_dipole"],
                "observed_magnitude": bootstrap["observed_magnitude"],
            },
            "bootstrap_per_host": {
                "n_boot": bootstrap_per_host["n_boot"],
                "n_units": bootstrap_per_host["n_units"],
                "per_host": bootstrap_per_host["per_host"],
                "sigma68_deg": bootstrap_per_host["sigma68_deg"],
                "median_deg": bootstrap_per_host["median_deg"],
            },
            "method_dipoles": method_dipoles,
            "kepler_excision": excision,
        },
        "spectrum": {
            "nside": spectrum["nside"],
            "lmax": spectrum["lmax"],
            "weight": spectrum["weight"],
            "ell": spectrum["ell"],
            "pseudo": spectrum["pseudo"],
            "masked": spectrum["masked"],
            "occupancy_fraction": spectrum["occupancy_fraction"],
            "null": {
                "n_null": spectrum_null["n_null"],
                "n_worlds": spectrum_null["n_worlds"],
                "p16": spectrum_null["p16"],
                "p50": spectrum_null["p50"],
                "p84": spectrum_null["p84"],
                "observed": spectrum_null["observed"],
                "z_score": spectrum_null["z_score"],
                "p_value": spectrum_null["p_value"],
            },
        },
        "methods": methods,
        "points": points,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
