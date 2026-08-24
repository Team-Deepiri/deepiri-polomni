"""Cai et al. (arXiv:2510.12134) bubble-collision template on RDF/RQF fields.

Analytic azimuthally symmetric pattern: linear potential → RDF dipole,
quadratic potential → RQF quadrupole, both aligned with collision axis n̂_c.
"""

from __future__ import annotations

import numpy as np

from polomni.observatory.pipeline.sources.bubble_collision_template import (
    bubble_template_score,
)
from polomni.observatory.pipeline.sources.quadratic_remote_field import (
    QuadraticFieldResult,
    _pixel_directions,
    _unit,
    axis_separation_deg,
)


def cai_bubble_template_maps(
    axis: np.ndarray,
    nside: int,
    *,
    A: float = 1.0,
    B: float = 0.65,
    mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Analytic RDF/RQF template maps for bubble collision about *axis*."""
    dirs = _pixel_directions(nside)
    mu = dirs @ _unit(axis)
    rdf = A * mu
    rqf = B * 0.5 * (3.0 * mu * mu - 1.0)
    if mask is not None:
        rdf = rdf.copy()
        rqf = rqf.copy()
        rdf[~mask] = 0.0
        rqf[~mask] = 0.0
    return rdf, rqf


def normalized_correlation(a: np.ndarray, b: np.ndarray, mask: np.ndarray) -> float:
    """Pearson correlation on masked pixels."""
    good = mask & np.isfinite(a) & np.isfinite(b)
    if int(np.sum(good)) < 10:
        return 0.0
    x = a[good] - float(np.mean(a[good]))
    y = b[good] - float(np.mean(b[good]))
    denom = float(np.linalg.norm(x) * np.linalg.norm(y))
    if denom < 1e-15:
        return 0.0
    return float(np.dot(x, y) / denom)


def match_cai_bubble_template(
    fields: QuadraticFieldResult,
    mask: np.ndarray,
    *,
    axis: np.ndarray | None = None,
    A: float = 1.0,
    B: float = 0.65,
) -> dict[str, float]:
    """Correlate reconstructed RDF/RQF maps with Cai bubble template."""
    import healpy as hp

    nside = hp.get_nside(fields.rdf_map)
    test_axis = _unit(axis if axis is not None else fields.dipole_axis)
    rdf_tpl, rqf_tpl = cai_bubble_template_maps(test_axis, nside, A=A, B=B, mask=mask)
    rdf_corr = normalized_correlation(fields.rdf_map, rdf_tpl, mask)
    rqf_corr = normalized_correlation(fields.rqf_map, rqf_tpl, mask)
    combined = 0.5 * (abs(rdf_corr) + abs(rqf_corr))
    rdf_s = float(np.sum(fields.rdf_map[mask] * rdf_tpl[mask]) / max(np.sum(mask), 1))
    rqf_s = float(np.sum(fields.rqf_map[mask] * rqf_tpl[mask]) / max(np.sum(mask), 1))
    tmpl_score = bubble_template_score(rdf_s, rqf_s)
    return {
        "axis": test_axis.tolist(),
        "rdf_correlation": round(rdf_corr, 4),
        "rqf_correlation": round(rqf_corr, 4),
        "combined_correlation": round(combined, 4),
        "template_score": round(tmpl_score, 6),
        "A": A,
        "B": B,
    }


def search_cai_template_axis(
    fields: QuadraticFieldResult,
    mask: np.ndarray,
    *,
    nside_dir: int = 8,
    A: float = 1.0,
    B: float = 0.65,
) -> tuple[np.ndarray, dict[str, float], np.ndarray]:
    """Grid search for collision axis maximizing Cai template correlation."""
    import healpy as hp

    grid = _pixel_directions(nside_dir)
    npix = hp.nside2npix(nside_dir)
    grid = grid[:npix]
    scores = np.zeros(npix)
    details: list[dict[str, float]] = []
    for i, ax in enumerate(grid):
        m = match_cai_bubble_template(fields, mask, axis=ax, A=A, B=B)
        scores[i] = m["combined_correlation"]
        details.append(m)
    idx = int(np.argmax(scores))
    return grid[idx], details[idx], scores
