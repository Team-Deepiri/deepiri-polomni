"""Vectorized anisotropy scoring and cached HEALPix geometry for axis search."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np

from polomni.observatory.scoring.radon_tomography import (
    DEFAULT_W_PARAMS,
    _prepare_map,
    rble_score_at_axis,
)


@dataclass
class PreparedCmbMap:
    """String-filtered CMB map cached for repeated axis scoring."""

    raw: np.ndarray
    filtered: np.ndarray
    W_params: dict[str, Any]

    @classmethod
    def from_map(
        cls,
        healpix_map: np.ndarray,
        *,
        W_params: dict[str, Any] | None = None,
    ) -> PreparedCmbMap:
        raw = np.asarray(healpix_map, dtype=float).ravel()
        params = W_params if W_params is not None else DEFAULT_W_PARAMS
        filtered = _prepare_map(raw, apply_string_filter=True, W_params=params)
        return cls(raw=raw, filtered=filtered, W_params=params)


@lru_cache(maxsize=32)
def _map_pixel_directions(nside: int) -> np.ndarray:
    """Cached unit direction per HEALPix pixel at *nside*."""
    import healpy as hp

    theta, phi = hp.pix2ang(nside, np.arange(hp.nside2npix(nside)))
    return np.column_stack(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
    )


def anisotropy_scores_batch(map_data: np.ndarray, directions: np.ndarray) -> np.ndarray:
    """Vectorized anisotropy proxy for all *directions* at once."""
    import healpy as hp

    map_data = np.asarray(map_data, dtype=float).ravel()
    directions = np.asarray(directions, dtype=float)
    if directions.ndim == 1:
        directions = directions.reshape(1, 3)
    nside = hp.get_nside(map_data)
    x = _map_pixel_directions(nside)
    mu = np.abs(x @ directions.T)
    par = map_data[:, None] * (mu > 0.9)
    orth = map_data[:, None] * (mu < 0.3)
    par_count = (mu > 0.9).sum(axis=0).clip(min=1)
    orth_count = (mu < 0.3).sum(axis=0).clip(min=1)
    par_std = np.sqrt(
        ((par**2).sum(axis=0) / par_count) - ((par.sum(axis=0) / par_count) ** 2)
    ).clip(min=0)
    orth_std = np.sqrt(
        ((orth**2).sum(axis=0) / orth_count) - ((orth.sum(axis=0) / orth_count) ** 2)
    ).clip(min=1e-12)
    return (par_std / orth_std).astype(float)


def score_axis_fast(
    prepared: PreparedCmbMap,
    axis: np.ndarray,
    *,
    n_eta: int = 24,
) -> float:
    """Fast S_RBLE at one axis (pixel geodesic profile, pre-filtered map)."""
    return rble_score_at_axis(
        prepared.filtered,
        axis,
        n_eta=n_eta,
        apply_string_filter=False,
        method="pixel",
    )


def score_axes_batch(
    prepared: PreparedCmbMap,
    axes: np.ndarray,
    *,
    n_eta: int = 24,
) -> np.ndarray:
    """Score many candidate axes sharing one filtered map."""
    axes = np.asarray(axes, dtype=float)
    if axes.ndim == 1:
        return np.array([score_axis_fast(prepared, axes, n_eta=n_eta)])
    return np.array([score_axis_fast(prepared, a, n_eta=n_eta) for a in axes])


@lru_cache(maxsize=16)
def healpix_direction_grid(dir_nside: int) -> np.ndarray:
    """Unit vectors for all pixels at *dir_nside* (cached)."""
    import healpy as hp

    theta, phi = hp.pix2ang(dir_nside, np.arange(hp.nside2npix(dir_nside)))
    return np.column_stack(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
    )


def sample_axes_in_cone(
    center: np.ndarray,
    *,
    cone_deg: float,
    n_samples: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Random unit vectors within *cone_deg* of *center*."""
    center = np.asarray(center, dtype=float)
    center = center / (np.linalg.norm(center) + 1e-15)
    cone_rad = np.radians(cone_deg)
    candidates: list[np.ndarray] = []
    for _ in range(n_samples):
        perturb = rng.standard_normal(3)
        perturb -= perturb @ center * center
        norm = np.linalg.norm(perturb)
        if norm < 1e-12:
            continue
        perturb /= norm
        angle = rng.uniform(0, cone_rad)
        cand = center * np.cos(angle) + perturb * np.sin(angle)
        candidates.append(cand / (np.linalg.norm(cand) + 1e-15))
    if not candidates:
        return center.reshape(1, 3)
    return np.stack(candidates)


def search_best_axis(
    prepared: PreparedCmbMap,
    *,
    dir_nside: int = 8,
    refine_cone_deg: float = 12.0,
    refine_samples: int = 16,
    search_n_eta: int = 16,
    seed: int = 0,
) -> tuple[np.ndarray, float, dict[str, Any]]:
    """Coarse HEALPix grid + local cone refinement on pre-filtered map."""
    rng = np.random.default_rng(seed)
    directions = healpix_direction_grid(dir_nside)
    coarse_scores = anisotropy_scores_batch(prepared.raw, directions)
    coarse_idx = int(np.argmax(coarse_scores))
    coarse_axis = directions[coarse_idx]
    coarse_score = float(coarse_scores[coarse_idx])

    candidates = sample_axes_in_cone(
        coarse_axis,
        cone_deg=refine_cone_deg,
        n_samples=refine_samples,
        rng=rng,
    )
    refine_scores = score_axes_batch(prepared, candidates, n_eta=max(search_n_eta, 24))
    refine_idx = int(np.argmax(refine_scores))
    refine_axis = candidates[refine_idx]
    refine_score = float(refine_scores[refine_idx])

    # Micro-refine top-3 candidates in a tight cone
    top_k = min(3, len(candidates))
    top_idx = np.argsort(refine_scores)[-top_k:]
    micro = sample_axes_in_cone(
        refine_axis,
        cone_deg=max(3.0, refine_cone_deg / 4),
        n_samples=8,
        rng=rng,
    )
    micro_scores = score_axes_batch(prepared, micro, n_eta=max(search_n_eta, 32))
    best_micro = int(np.argmax(micro_scores))
    if micro_scores[best_micro] > refine_score:
        refine_axis = micro[best_micro]
        refine_score = float(micro_scores[best_micro])

    meta = {
        "coarse_axis": coarse_axis.tolist(),
        "coarse_score": coarse_score,
        "refine_score": refine_score,
        "dir_nside": dir_nside,
        "search_n_eta": search_n_eta,
    }
    if refine_score >= coarse_score:
        return refine_axis, refine_score, meta
    return coarse_axis, coarse_score, meta
