"""Denser galaxy tracer + sensitivity forecast for the multiverse ladder.

Locksmith: ACT×DESI public catalogs are heavy; until ingested, stack every
all-sky / wide-angle tracer already in cache (PSCz + SDSS SpecObj) and
**forecast** Fisher SNR under DESI-LRG-class N_gal / f_sky. That proves the
scaling math without waiting on a multi-TB download.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.sources.iras_pscz import load_pscz_catalog
from polomni.observatory.pipeline.sources.sky_frames import equatorial_to_galactic


# Rough DESI LRG DR1-class order-of-magnitude (public summaries)
DESI_LRG_N_GAL_FORECAST = 2.0e6
DESI_LRG_F_SKY_FORECAST = 0.35


def _unique_unit_vectors(vecs: np.ndarray, *, decimals: int = 4) -> np.ndarray:
    v = np.asarray(vecs, dtype=float)
    if v.size == 0:
        return v.reshape(0, 3)
    # Quantize for dedup across overlapping footprints
    key = np.round(v, decimals)
    _, idx = np.unique(key, axis=0, return_index=True)
    return v[np.sort(idx)]


def load_dense_tracer_galactic(
    *,
    cache: DataCache | None = None,
    include_sdss: bool = True,
) -> dict[str, Any]:
    """Combine PSCz + optional SDSS galaxies into a denser Galactic tracer."""
    cache = cache or DataCache()
    cat = load_pscz_catalog()
    parts: list[np.ndarray] = [equatorial_to_galactic(cat["vecs_eq"])]
    sources = ["iras_pscz"]
    n_pscz = int(cat["vecs_eq"].shape[0])
    n_sdss = 0

    if include_sdss:
        from polomni.observatory.pipeline.sources.cross_sky import load_galaxy_vectors

        for pid in ("sdss_bao_ladder", "sdss_galaxies"):
            path = cache.resolved_path(pid)
            if path is None:
                cand = cache.root / pid
                if cand.is_dir():
                    jsons = list(cand.glob("*.json"))
                    path = jsons[0] if jsons else None
            if path is None or not Path(path).is_file():
                continue
            try:
                eq = load_galaxy_vectors(path)
                if eq.shape[0] < 50:
                    continue
                parts.append(equatorial_to_galactic(eq))
                sources.append(pid)
                n_sdss += int(eq.shape[0])
            except Exception:
                continue

    stacked = _unique_unit_vectors(np.vstack(parts))
    return {
        "vecs_gal": stacked,
        "n_galaxies": int(stacked.shape[0]),
        "n_pscz": n_pscz,
        "n_sdss": n_sdss,
        "sources": sources,
        "z": None,  # heterogeneous; multi-z stays PSCz-only
    }


def forecast_fisher_snr(
    snr_now: float,
    *,
    n_gal_now: int,
    n_gal_future: float = DESI_LRG_N_GAL_FORECAST,
    f_sky_now: float = 0.65,
    f_sky_future: float = DESI_LRG_F_SKY_FORECAST,
) -> dict[str, Any]:
    """Scale Fisher SNR ∝ √(N_gal · f_sky) under shot-noise–limited tomography."""
    n0 = max(float(n_gal_now), 1.0)
    f0 = max(float(f_sky_now), 1e-3)
    scale = float(np.sqrt((n_gal_future / n0) * (f_sky_future / f0)))
    snr_f = float(snr_now) * scale
    return {
        "snr_now": round(float(snr_now), 4),
        "snr_forecast": round(snr_f, 4),
        "scale_factor": round(scale, 4),
        "n_gal_now": int(n_gal_now),
        "n_gal_future": int(n_gal_future),
        "f_sky_now": round(f0, 4),
        "f_sky_future": round(float(f_sky_future), 4),
        "assumption": "shot-noise limited RDF/RQF; same bubble amplitude",
        "passes_snr_2_forecast": bool(snr_f > 2.0),
    }


def dense_tracer_report(
    *,
    snr_now: float,
    f_sky_now: float = 0.65,
    cache: DataCache | None = None,
) -> dict[str, Any]:
    """Package denser tracer census + DESI-class forecast."""
    dense = load_dense_tracer_galactic(cache=cache)
    forecast = forecast_fisher_snr(
        snr_now,
        n_gal_now=dense["n_galaxies"],
        f_sky_now=f_sky_now,
    )
    return {
        "phase": "G_dense_tracer_forecast",
        "tracer": {
            "n_galaxies": dense["n_galaxies"],
            "n_pscz": dense["n_pscz"],
            "n_sdss": dense["n_sdss"],
            "sources": dense["sources"],
        },
        "forecast_desi_lrg_class": forecast,
        "interpretation": (
            "Forecast SNR>2 under DESI-LRG-class N — motivates public LRG ingest"
            if forecast["passes_snr_2_forecast"]
            else "Even DESI-class scaling may be marginal at current amplitude — "
            "need stronger bubble template or multi-z kernels"
        ),
    }
