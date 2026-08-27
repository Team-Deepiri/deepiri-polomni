"""CMB sky masking for clean-sky preferred-axis measurement.

WMAP preferred axes near the Galactic plane (b≈0°) are foreground-suspect.
Apply the Planck intensity confidence mask (when cached) plus a |b| cut so
hierarchical search only sees the same clean sky used in bubble/P1 work.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from polomni.observatory.ingest.healpix_loader import downsample_map, load_healpix_map, map_nside
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.sources.bubble_collisions import galactic_edge_mask


def load_planck_intensity_mask(nside: int, cache: DataCache | None = None) -> np.ndarray | None:
    """Boolean keep-mask at *nside* from cached ``planck_int_mask`` (1=keep)."""
    cache = cache or DataCache()
    path = cache.resolved_path("planck_int_mask")
    if path is None:
        cand = cache.root / "planck_int_mask" / "planck_cmb_int_mask.fits"
        path = cand if cand.exists() else None
    if path is None or not path.exists():
        return None
    raw = load_healpix_map(path)
    # Mask FITS may be nside 2048; downsample with majority vote via mean.
    down = downsample_map(np.asarray(raw, dtype=float), nside)
    return down > 0.5


def apply_clean_sky_mask(
    cmb: np.ndarray,
    *,
    nside: int | None = None,
    cache: DataCache | None = None,
    b_cut_deg: float = 20.0,
    fill: str = "mean",
) -> tuple[np.ndarray, dict[str, Any]]:
    """Zero (or mean-fill) Galactic-plane / Planck-masked pixels.

    Returns (masked_map, meta) with ``f_sky`` and which masks applied.
    """
    arr = np.asarray(cmb, dtype=float).ravel().copy()
    nside = nside or map_nside(arr)
    edge = galactic_edge_mask(nside, b_cut_deg)
    planck = load_planck_intensity_mask(nside, cache)
    if planck is not None and planck.size == arr.size:
        keep = edge & planck
        used_planck = True
    else:
        keep = edge
        used_planck = False

    if fill == "mean" and keep.any():
        fill_val = float(np.mean(arr[keep]))
    else:
        fill_val = 0.0
    arr[~keep] = fill_val
    return arr, {
        "f_sky": float(keep.mean()),
        "b_cut_deg": float(b_cut_deg),
        "planck_int_mask": used_planck,
        "n_kept": int(keep.sum()),
        "nside": int(nside),
    }


def galactic_latitude_cut(vecs_galactic: np.ndarray, b_cut_deg: float = 20.0) -> np.ndarray:
    """Boolean mask: keep catalog vectors with |b| ≥ *b_cut_deg* (Galactic frame)."""
    import healpy as hp

    v = np.asarray(vecs_galactic, dtype=float)
    if v.ndim == 1:
        v = v.reshape(1, 3)
    theta, _phi = hp.vec2ang(v)
    b = 90.0 - np.degrees(theta)
    return np.abs(b) >= b_cut_deg
