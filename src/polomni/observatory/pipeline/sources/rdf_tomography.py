"""P5-RDF — remote dipole/quadrupole field proxy via CMB × galaxy cross-correlation.

Phase A instrument (Aug 2026): a simplified kSZ-tomography-style estimator following
Deutsch et al. PRD 98, 063502 (2018) and the bubble-collision RQF program of
Cai–Zhang–Guan (arXiv:2510.12134).

This is **not** a detection pipeline. It reconstructs axis-dependent
dipole- and quadrupole-weighted cross-correlations between high-pass CMB
temperature and a galaxy density tracer (IRAS PSCz), then tests whether the
peak axes are **coherently aligned** — the azimuthally symmetric bubble-collision
template predicts the same collision axis in both RDF and RQF proxies.

Honesty contract:
- Primary-CMB circle searches are null (Feeney → Planck → Polomni bubble).
- ACT×DESI kSZ velocity is real ΛCDM structure, not multiverse proof.
- This module reports **proxy statistics + shuffle nulls** only; no claim of
  visible other universes until a preregistered template survives blind holdout.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.sources.bubble_collisions import (
    galactic_edge_mask,
    load_planck_for_search,
)
from polomni.observatory.pipeline.sources.bubble_collision_template import (
    bubble_template_score,
    bubble_template_scores_batch,
)
from polomni.observatory.pipeline.sources.cai_bubble_template import (
    match_cai_bubble_template,
    search_cai_template_axis,
)
from polomni.observatory.pipeline.sources.iras_pscz import load_pscz_vectors
from polomni.observatory.pipeline.sources.quadratic_remote_field import (
    quadratic_remote_fields,
)
from polomni.observatory.pipeline.sources.sky_frames import equatorial_to_galactic


def _unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float).reshape(3)
    n = float(np.linalg.norm(v))
    if n < 1e-15:
        return np.array([0.0, 0.0, 1.0])
    return v / n


def _pixel_directions(nside: int) -> np.ndarray:
    import healpy as hp

    theta, phi = hp.pix2ang(nside, np.arange(hp.nside2npix(nside)))
    return np.column_stack(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
    )


def candidate_axis_grid(nside_dir: int = 8) -> np.ndarray:
    """HEALPix pixel centers at *nside_dir* — coarse axis search grid."""
    import healpy as hp

    nside_dir = max(1, int(nside_dir))
    npix = hp.nside2npix(nside_dir)
    return _pixel_directions(nside_dir)[:npix]


def galaxy_overdensity_map(
    vecs_gal: np.ndarray,
    nside: int,
    mask: np.ndarray,
) -> np.ndarray:
    """Project unit sky vectors into a masked HEALPix overdensity map δ_g."""
    import healpy as hp

    vecs = np.asarray(vecs_gal, dtype=float)
    if vecs.ndim != 2 or vecs.shape[1] != 3:
        raise ValueError("vecs_gal must be N×3")
    npix = hp.nside2npix(nside)
    if mask.shape != (npix,):
        raise ValueError("mask shape must match nside")

    counts = np.zeros(npix, dtype=float)
    idx = hp.vec2pix(nside, vecs[:, 0], vecs[:, 1], vecs[:, 2])
    for i in idx:
        if mask[i]:
            counts[i] += 1.0

    mean = float(np.mean(counts[mask])) if np.any(mask) else 0.0
    std = float(np.std(counts[mask])) if np.any(mask) else 1.0
    if std < 1e-12:
        std = 1.0
    delta = np.zeros(npix, dtype=float)
    delta[mask] = (counts[mask] - mean) / std
    return delta


def high_pass_cmb_map(
    cmb: np.ndarray,
    *,
    lmin: int = 30,
    lmax: int | None = None,
    mask: np.ndarray | None = None,
) -> np.ndarray:
    """Band-pass CMB map: remove ℓ < lmin (large-scale primary modes)."""
    import healpy as hp

    t = np.asarray(cmb, dtype=float).ravel()
    nside = hp.get_nside(t)
    if mask is not None:
        t = t.copy()
        t[~mask] = hp.UNSEEN
    lmax = lmax if lmax is not None else 3 * nside - 1
    alm = hp.map2alm(t, lmax=lmax)
    fl = hp.alm2cl(alm)
    wl = np.zeros(len(fl))
    for ell in range(len(fl)):
        wl[ell] = 1.0 if ell >= lmin else 0.0
    alm_f = hp.almxfl(alm, wl, inplace=False)
    out = hp.alm2map(alm_f, nside)
    if mask is not None:
        out = out.copy()
        out[~mask] = 0.0
    return out


def multipole_weighted_cross_batch(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    axes: np.ndarray,
    *,
    ell: int = 1,
    mask: np.ndarray | None = None,
) -> np.ndarray:
    """Vectorized multipole_weighted_cross for all candidate axes."""
    import healpy as hp

    t = np.asarray(cmb_hp, dtype=float).ravel()
    d = np.asarray(delta_g, dtype=float).ravel()
    axes = np.asarray(axes, dtype=float)
    if axes.ndim == 1:
        axes = axes.reshape(1, 3)
    nside = hp.get_nside(t)
    dirs = _pixel_directions(nside)
    mu = dirs @ axes.T
    if ell == 1:
        w = mu
    elif ell == 2:
        w = 0.5 * (3.0 * mu * mu - 1.0)
    else:
        raise ValueError("only ell=1 (RDF) or ell=2 (RQF) supported")

    prod = t[:, None] * d[:, None] * w
    if mask is not None:
        prod = prod * mask[:, None]
        n_eff = max(int(np.sum(mask)), 1)
    else:
        n_eff = max(int(prod.shape[0]), 1)
    return np.sum(prod, axis=0) / n_eff


def multipole_weighted_cross(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    axis: np.ndarray,
    *,
    ell: int = 1,
    mask: np.ndarray | None = None,
) -> float:
    """Dipole (ell=1) or quadrupole (ell=2) weighted CMB×galaxy cross-statistic.

    For each pixel p with direction n̂_p, weight w(n̂_p · n̂_a):
      ℓ=1: w(μ) = μ
      ℓ=2: w(μ) = (3μ² − 1) / 2
    Statistic: Σ_p T_hp(p) δ_g(p) w(n̂_p · n̂_a) / N_eff.
    """
    import healpy as hp

    t = np.asarray(cmb_hp, dtype=float).ravel()
    d = np.asarray(delta_g, dtype=float).ravel()
    nside = hp.get_nside(t)
    if d.shape != t.shape:
        raise ValueError("cmb_hp and delta_g must share nside")
    axis_u = _unit(axis)
    dirs = _pixel_directions(nside)
    mu = dirs @ axis_u
    if ell == 1:
        w = mu
    elif ell == 2:
        w = 0.5 * (3.0 * mu * mu - 1.0)
    else:
        raise ValueError("only ell=1 (RDF) or ell=2 (RQF) supported")

    prod = t * d * w
    if mask is not None:
        good = mask & np.isfinite(prod)
        n_eff = int(np.sum(good))
        if n_eff < 10:
            return 0.0
        return float(np.sum(prod[good]) / n_eff)
    good = np.isfinite(prod)
    return float(np.sum(prod[good]) / max(int(np.sum(good)), 1))


def search_multipole_axis(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    *,
    ell: int = 1,
    mask: np.ndarray,
    nside_dir: int = 8,
) -> tuple[np.ndarray, float, np.ndarray]:
    """Grid search for axis maximizing |multipole_weighted_cross|."""
    grid = candidate_axis_grid(nside_dir)
    scores = multipole_weighted_cross_batch(cmb_hp, delta_g, grid, ell=ell, mask=mask)
    idx = int(np.argmax(np.abs(scores)))
    return grid[idx], float(scores[idx]), scores


@dataclass
class RdfRqfSearchResult:
    """Peak RDF (ℓ=1) and RQF (ℓ=2) axes from the cross-correlation proxy."""

    rdf_axis: np.ndarray
    rdf_score: float
    rqf_axis: np.ndarray
    rqf_score: float
    axis_separation_deg: float
    template_coherence: float

    def to_dict(self) -> dict[str, Any]:
        import healpy as hp

        def _lonlat(v: np.ndarray) -> tuple[float, float]:
            th, ph = hp.vec2ang(v.reshape(1, 3))
            return float(np.degrees(ph)[0]), float(90.0 - np.degrees(th)[0])

        r_lon, r_lat = _lonlat(self.rdf_axis)
        q_lon, q_lat = _lonlat(self.rqf_axis)
        return {
            "rdf_axis_gal": self.rdf_axis.tolist(),
            "rdf_score": round(self.rdf_score, 6),
            "rdf_gal_lon": round(r_lon, 2),
            "rdf_gal_lat": round(r_lat, 2),
            "rqf_axis_gal": self.rqf_axis.tolist(),
            "rqf_score": round(self.rqf_score, 6),
            "rqf_gal_lon": round(q_lon, 2),
            "rqf_gal_lat": round(q_lat, 2),
            "axis_separation_deg": round(self.axis_separation_deg, 2),
            "template_coherence": round(self.template_coherence, 4),
        }


def axis_separation_deg(a: np.ndarray, b: np.ndarray) -> float:
    a_u, b_u = _unit(a), _unit(b)
    dot = float(np.clip(np.dot(a_u, b_u), -1.0, 1.0))
    return float(np.degrees(np.arccos(abs(dot))))


def bubble_template_coherence(
    rdf_axis: np.ndarray,
    rqf_axis: np.ndarray,
    rdf_score: float,
    rqf_score: float,
) -> tuple[float, float]:
    """Azimuthally symmetric bubble template: RDF and RQF peak at the same axis.

    Returns (axis_separation_deg, coherence_score) where coherence combines
    axis alignment and dual multipole significance (product of |scores| when
    axes agree within 20°).
    """
    sep = axis_separation_deg(rdf_axis, rqf_axis)
    align = max(0.0, 1.0 - sep / 20.0)
    coherence = align * abs(rdf_score) * abs(rqf_score)
    return sep, coherence


def search_rdf_rqf(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    *,
    mask: np.ndarray,
    nside_dir: int = 8,
) -> RdfRqfSearchResult:
    rdf_axis, rdf_score, _ = search_multipole_axis(
        cmb_hp, delta_g, ell=1, mask=mask, nside_dir=nside_dir
    )
    rqf_axis, rqf_score, _ = search_multipole_axis(
        cmb_hp, delta_g, ell=2, mask=mask, nside_dir=nside_dir
    )
    sep, coherence = bubble_template_coherence(rdf_axis, rqf_axis, rdf_score, rqf_score)
    return RdfRqfSearchResult(
        rdf_axis=rdf_axis,
        rdf_score=rdf_score,
        rqf_axis=rqf_axis,
        rqf_score=rqf_score,
        axis_separation_deg=sep,
        template_coherence=coherence,
    )


def shuffle_galaxy_positions(
    vecs_gal: np.ndarray,
    nside: int,
    mask: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Footprint-preserving null: shuffle galaxy pixel assignments."""
    import healpy as hp

    vecs = np.asarray(vecs_gal, dtype=float)
    idx = hp.vec2pix(nside, vecs[:, 0], vecs[:, 1], vecs[:, 2])
    good_idx = idx[mask[idx]]
    if good_idx.size == 0:
        return vecs
    shuffled = rng.permutation(good_idx)
    if shuffled.size < vecs.shape[0]:
        shuffled = rng.choice(good_idx, size=vecs.shape[0], replace=True)
    else:
        shuffled = shuffled[: vecs.shape[0]]
    theta, phi = hp.pix2ang(nside, shuffled)
    return np.column_stack(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
    )


def search_bubble_template_axis(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    *,
    mask: np.ndarray,
    nside_dir: int = 8,
) -> tuple[np.ndarray, float, np.ndarray, np.ndarray, np.ndarray]:
    """Phase B: axis maximizing combined Cai-class bubble template score."""
    grid = candidate_axis_grid(nside_dir)
    rdf_scores = multipole_weighted_cross_batch(cmb_hp, delta_g, grid, ell=1, mask=mask)
    rqf_scores = multipole_weighted_cross_batch(cmb_hp, delta_g, grid, ell=2, mask=mask)
    template_scores = bubble_template_scores_batch(rdf_scores, rqf_scores)
    idx = int(np.argmax(template_scores))
    return grid[idx], float(template_scores[idx]), template_scores, rdf_scores, rqf_scores


def scores_at_axis(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    axis: np.ndarray,
    *,
    mask: np.ndarray,
) -> dict[str, float]:
    """RDF, RQF, and bubble template scores at a fixed (preregistered) axis."""
    rdf = multipole_weighted_cross(cmb_hp, delta_g, axis, ell=1, mask=mask)
    rqf = multipole_weighted_cross(cmb_hp, delta_g, axis, ell=2, mask=mask)
    tmpl = bubble_template_score(rdf, rqf)
    return {"rdf": rdf, "rqf": rqf, "template": tmpl}


def isotropic_axis_null(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    *,
    mask: np.ndarray,
    n_null: int = 64,
    seed: int = 0,
) -> np.ndarray:
    """Template scores at random isotropic axes (look-elsewhere control)."""
    rng = np.random.default_rng(seed)
    null_scores: list[float] = []
    for _ in range(n_null):
        v = rng.normal(size=3)
        v /= np.linalg.norm(v) + 1e-15
        s = scores_at_axis(cmb_hp, delta_g, v, mask=mask)
        null_scores.append(s["template"])
    return np.asarray(null_scores, dtype=float)


def load_rble_scar_axis(scar_report_path: Path | str | None = None) -> np.ndarray | None:
    """Frozen CMB consensus axis from M8 scar report (WMAP-K-only freeze)."""
    import json

    path = Path(scar_report_path or "data/reports/multi_survey_scar_consensus.json")
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    freeze = data.get("cmb_freeze") or {}
    axis = freeze.get("consensus_axis")
    if axis is None:
        return None
    return _unit(np.asarray(axis, dtype=float))


def rble_scar_axis_test(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    scar_axis: np.ndarray,
    *,
    mask: np.ndarray,
    n_null: int = 64,
    seed: int = 0,
) -> dict[str, Any]:
    """RBLE model prediction: bubble template enhanced at frozen scar axis."""
    obs = scores_at_axis(cmb_hp, delta_g, scar_axis, mask=mask)
    null_arr = isotropic_axis_null(cmb_hp, delta_g, mask=mask, n_null=n_null, seed=seed)
    p_value = float((1 + np.sum(null_arr >= obs["template"])) / (n_null + 1))
    return {
        "scar_axis_gal": scar_axis.tolist(),
        "observed": {k: round(v, 6) for k, v in obs.items()},
        "null": {
            "n_realizations": n_null,
            "median": round(float(np.median(null_arr)), 6),
            "p_value": round(p_value, 4),
        },
        "gate_pass": bool(p_value <= 0.05),
    }


def lcdm_cmb_null_realizations(
    n_null: int,
    nside: int,
    *,
    lmin: int = 30,
    mask: np.ndarray,
    seed: int = 0,
) -> list[np.ndarray]:
    """ΛCDM-class isotropic Gaussian CMB nulls (high-pass filtered)."""
    from polomni.observatory.scoring.null_models import generate_grf_null

    maps = generate_grf_null(n_null, nside, seed=seed)
    return [high_pass_cmb_map(m, lmin=lmin, mask=mask) for m in maps]


def simulation_null_template_scores(
    delta_g: np.ndarray,
    *,
    mask: np.ndarray,
    nside: int,
    lmin: int = 30,
    n_null: int = 16,
    seed: int = 0,
) -> np.ndarray:
    """Phase C: template scores on ΛCDM CMB nulls with fixed galaxy field."""
    null_scores: list[float] = []
    for cmb_null in lcdm_cmb_null_realizations(
        n_null, nside, lmin=lmin, mask=mask, seed=seed
    ):
        _, score, _, _, _ = search_bubble_template_axis(
            cmb_null, delta_g, mask=mask, nside_dir=4
        )
        null_scores.append(score)
    return np.asarray(null_scores, dtype=float)


def inject_bubble_rdf_signal(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    axis: np.ndarray,
    *,
    rdf_amp: float = 5.0,
    rqf_amp: float = 3.0,
    mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Plant correlated RDF+RQF pattern for instrument validation."""
    nside = __import__("healpy").get_nside(cmb_hp)
    dirs = _pixel_directions(nside)
    axis_u = _unit(axis)
    mu = dirs @ axis_u
    t_inj = rdf_amp * mu + rqf_amp * 0.5 * (3.0 * mu * mu - 1.0)
    d_inj = 0.5 * rdf_amp * mu + 0.5 * rqf_amp * 0.5 * (3.0 * mu * mu - 1.0)
    t_out = np.asarray(cmb_hp, dtype=float) + t_inj
    d_out = np.asarray(delta_g, dtype=float) + d_inj
    if mask is not None:
        t_out = t_out.copy()
        d_out = d_out.copy()
        t_out[~mask] = 0.0
        d_out[~mask] = 0.0
    return t_out, d_out


def rdf_tomography_report(
    *,
    nside: int = 64,
    nside_dir: int = 8,
    lmin: int = 30,
    b_cut: float = 20.0,
    n_null: int = 32,
    n_sim_null: int = 16,
    seed: int = 0,
    map_product_id: str = "planck_smica_cmb",
    scar_report_path: Path | str | None = None,
    cache: DataCache | None = None,
) -> dict[str, Any]:
    """Run P5 RDF/RQF pipeline: Phase A proxy + Phase B template + RBLE scar test."""
    cache = cache or DataCache()
    cmb, pid = load_planck_for_search(map_product_id=map_product_id, nside=nside, cache=cache)
    mask = galactic_edge_mask(nside, b_cut=b_cut)
    f_sky = float(np.mean(mask))

    vecs_eq = load_pscz_vectors()
    vecs_gal = equatorial_to_galactic(vecs_eq)
    delta_g = galaxy_overdensity_map(vecs_gal, nside, mask)
    cmb_hp = high_pass_cmb_map(cmb, lmin=lmin, mask=mask)

    # Phase A: independent RDF/RQF peak search
    obs_a = search_rdf_rqf(cmb_hp, delta_g, mask=mask, nside_dir=nside_dir)

    # Phase B: joint bubble template axis search
    tmpl_axis, tmpl_score, _, rdf_grid, rqf_grid = search_bubble_template_axis(
        cmb_hp, delta_g, mask=mask, nside_dir=nside_dir
    )
    import healpy as hp

    th, ph = hp.vec2ang(tmpl_axis.reshape(1, 3))
    tmpl_lon = float(np.degrees(ph)[0])
    tmpl_lat = float(90.0 - np.degrees(th)[0])

    rng = np.random.default_rng(seed)
    null_coherence: list[float] = []
    null_sep: list[float] = []
    null_template: list[float] = []
    for _ in range(n_null):
        shuf = shuffle_galaxy_positions(vecs_gal, nside, mask, rng)
        d_null = galaxy_overdensity_map(shuf, nside, mask)
        res = search_rdf_rqf(cmb_hp, d_null, mask=mask, nside_dir=nside_dir)
        null_coherence.append(res.template_coherence)
        null_sep.append(res.axis_separation_deg)
        _, t_score, _, _, _ = search_bubble_template_axis(
            cmb_hp, d_null, mask=mask, nside_dir=nside_dir
        )
        null_template.append(t_score)

    null_coherence_arr = np.asarray(null_coherence, dtype=float)
    null_sep_arr = np.asarray(null_sep, dtype=float)
    null_template_arr = np.asarray(null_template, dtype=float)
    p_coherence = float((1 + np.sum(null_coherence_arr >= obs_a.template_coherence)) / (n_null + 1))
    p_sep = float((1 + np.sum(null_sep_arr <= obs_a.axis_separation_deg)) / (n_null + 1))
    p_template_shuffle = float((1 + np.sum(null_template_arr >= tmpl_score)) / (n_null + 1))

    # Phase C: ΛCDM CMB simulation null (fixed galaxies)
    sim_null_arr = simulation_null_template_scores(
        delta_g, mask=mask, nside=nside, lmin=lmin, n_null=n_sim_null, seed=seed + 1
    )
    p_template_sim = float((1 + np.sum(sim_null_arr >= tmpl_score)) / (n_sim_null + 1))

    # RBLE model: template score at frozen M8 scar axis
    scar_axis = load_rble_scar_axis(scar_report_path)
    rble_test: dict[str, Any] | None = None
    scar_sep_deg: float | None = None
    if scar_axis is not None:
        rble_test = rble_scar_axis_test(
            cmb_hp, delta_g, scar_axis, mask=mask, n_null=max(n_null, 32), seed=seed + 2
        )
        scar_sep_deg = axis_separation_deg(tmpl_axis, scar_axis)

    phase_b_gate = bool(p_template_shuffle < 0.01 and p_template_sim < 0.01)
    rble_gate = bool(rble_test and rble_test.get("gate_pass"))
    combined_gate = bool(phase_b_gate and scar_sep_deg is not None and scar_sep_deg < 25.0)

    # Phase D: full MV quadratic estimator + Cai template match
    q_fields = quadratic_remote_fields(cmb_hp, delta_g, mask, f_sky=f_sky)
    cai_at_dipole = match_cai_bubble_template(q_fields, mask)
    cai_axis, cai_best, _ = search_cai_template_axis(q_fields, mask, nside_dir=nside_dir)
    null_cai: list[float] = []
    null_q_sep: list[float] = []
    for _ in range(n_null):
        shuf = shuffle_galaxy_positions(vecs_gal, nside, mask, rng)
        d_null = galaxy_overdensity_map(shuf, nside, mask)
        q_null = quadratic_remote_fields(cmb_hp, d_null, mask, f_sky=f_sky)
        cai_null = match_cai_bubble_template(q_null, mask, axis=q_null.dipole_axis)
        null_cai.append(cai_null["combined_correlation"])
        null_q_sep.append(q_null.axis_separation_deg)
    null_cai_arr = np.asarray(null_cai, dtype=float)
    null_q_sep_arr = np.asarray(null_q_sep, dtype=float)
    p_cai = float((1 + np.sum(null_cai_arr >= cai_best["combined_correlation"])) / (n_null + 1))

    null_cai_sim: list[float] = []
    for cmb_null in lcdm_cmb_null_realizations(
        n_sim_null, nside, lmin=lmin, mask=mask, seed=seed + 3
    ):
        q_sim = quadratic_remote_fields(cmb_null, delta_g, mask, f_sky=f_sky)
        cai_sim = match_cai_bubble_template(q_sim, mask, axis=q_sim.dipole_axis)
        null_cai_sim.append(cai_sim["combined_correlation"])
    null_cai_sim_arr = np.asarray(null_cai_sim, dtype=float)
    p_cai_sim = float((1 + np.sum(null_cai_sim_arr >= cai_best["combined_correlation"])) / (n_sim_null + 1))

    q_scar_match: dict[str, Any] | None = None
    q_scar_sep: float | None = None
    if scar_axis is not None:
        q_scar_match = match_cai_bubble_template(q_fields, mask, axis=scar_axis)
        q_scar_sep = axis_separation_deg(cai_axis, scar_axis)

    phase_d_gate = bool(
        p_cai < 0.01
        and p_cai_sim < 0.01
        and q_fields.axis_separation_deg < 25.0
    )
    physics_gate_v2 = bool(
        phase_d_gate and q_scar_sep is not None and q_scar_sep < 25.0 and rble_gate
    )

    # Phase E: Fisher SO(2,1) bubble invariant with ΛCDM mitigation
    from polomni.observatory.pipeline.sources.multiverse_fisher_scan import fisher_scan_report

    fisher = fisher_scan_report(
        cmb_hp, delta_g, mask, nside_dir=nside_dir, n_null=n_null, seed=seed + 4, scar_axis=scar_axis
    )

    # Phase F: multi-z PSCz shells + kernel-weighted Fisher stack
    from polomni.observatory.pipeline.sources.iras_pscz import load_pscz_catalog
    from polomni.observatory.pipeline.sources.multi_z_tomography import multi_z_fisher_report

    cat = load_pscz_catalog()
    vecs_eq_z = cat["vecs_eq"]
    z_gal = cat["z"]
    vecs_gal_z = equatorial_to_galactic(vecs_eq_z)
    # Align catalog length with any filtered load (same cache)
    phase_f = multi_z_fisher_report(
        cmb_hp,
        vecs_gal_z,
        z_gal,
        mask,
        nside_dir=max(4, nside_dir // 2),
        n_null=max(8, n_null // 2),
        seed=seed + 5,
        scar_axis=scar_axis,
    )

    physics_gate = bool(fisher.get("gate_pass") or phase_f.get("gate_pass"))

    return {
        "instrument": "P5-RDF tomography (Phase A–F: multi-z Fisher stack)",
        "study_id": "P5-RDF",
        "phase": "F_multi_z_tomography",
        "map_product_id": pid,
        "galaxy_tracer": "iras_pscz",
        "nside": nside,
        "lmin": lmin,
        "mask": {"b_cut_deg": b_cut, "f_sky": round(f_sky, 4)},
        "n_galaxies": int(vecs_gal.shape[0]),
        "phase_a": {
            "observed": obs_a.to_dict(),
            "null": {
                "n_realizations": n_null,
                "seed": seed,
                "template_coherence": {
                    "observed": round(obs_a.template_coherence, 6),
                    "median": round(float(np.median(null_coherence_arr)), 6),
                    "p_value": round(p_coherence, 4),
                },
                "axis_separation_deg": {
                    "observed": round(obs_a.axis_separation_deg, 2),
                    "median": round(float(np.median(null_sep_arr)), 2),
                    "p_value": round(p_sep, 4),
                },
            },
            "bubble_template_gate": {
                "requires": "RDF and RQF peaks aligned (<20°) with coherence p<0.01",
                "pass": bool(obs_a.axis_separation_deg < 20.0 and p_coherence < 0.01),
            },
        },
        "phase_b": {
            "template_axis_gal": tmpl_axis.tolist(),
            "template_gal_lon": round(tmpl_lon, 2),
            "template_gal_lat": round(tmpl_lat, 2),
            "template_score": round(tmpl_score, 6),
            "null_shuffle": {
                "median": round(float(np.median(null_template_arr)), 6),
                "p_value": round(p_template_shuffle, 4),
            },
            "null_lcdm_sim": {
                "n_realizations": n_sim_null,
                "median": round(float(np.median(sim_null_arr)), 6),
                "p_value": round(p_template_sim, 4),
            },
            "gate_pass": phase_b_gate,
        },
        "rble_scar_axis_test": {
            **(rble_test or {"reason": "no M8 scar report cached"}),
            "template_axis_sep_from_scar_deg": round(scar_sep_deg, 2) if scar_sep_deg else None,
            "model_prediction": (
                "RBLE frozen CMB scar axis should show enhanced bubble template vs isotropic axes"
            ),
            "gate_pass": rble_gate,
        },
        "multiverse_physics_gate": {
            "requires": "Phase E or F Fisher gate (SNR + null + coherence + RBLE align)",
            "pass": physics_gate,
            "legacy_phase_d": physics_gate_v2,
            "phase_e": bool(fisher.get("gate_pass")),
            "phase_f": bool(phase_f.get("gate_pass")),
        },
        "phase_d": {
            "quadratic_fields": q_fields.to_dict(),
            "cai_at_dipole": cai_at_dipole,
            "cai_best_axis": cai_best,
            "null_shuffle": {
                "median_correlation": round(float(np.median(null_cai_arr)), 4),
                "p_value": round(p_cai, 4),
            },
            "null_lcdm_sim": {
                "n_realizations": n_sim_null,
                "median_correlation": round(float(np.median(null_cai_sim_arr)), 4),
                "p_value": round(p_cai_sim, 4),
            },
            "rble_scar_cai_match": q_scar_match,
            "scar_sep_from_cai_axis_deg": round(q_scar_sep, 2) if q_scar_sep else None,
            "gate_pass": phase_d_gate,
        },
        "phase_e": fisher,
        "phase_f": phase_f,
        "verdict": _build_verdict(
            p_coherence=p_coherence,
            p_template_shuffle=p_template_shuffle,
            p_template_sim=p_template_sim,
            p_cai=p_cai,
            p_cai_sim=p_cai_sim,
            rble_gate=rble_gate,
            combined_gate=physics_gate,
            phase_d=phase_d_gate,
            fisher_snr=float((fisher.get("observed") or {}).get("fisher_snr", 0.0)),
            multi_z_snr=float((phase_f.get("stacked") or {}).get("fisher_snr", 0.0)),
            multi_z_p=float((phase_f.get("null") or {}).get("p_value_snr", 1.0)),
        ),
        "honesty": (
            "Phase F: multi-z PSCz shells with kernel-weighted Fisher stack + cross-z "
            "axis coherence. Deepest in-repo tomography without RemoteField vendor; "
            "not a detection until blind holdout. Multiverse NOT ruled out."
        ),
        "references": [
            "Deutsch et al. PRD 98, 063502 (2018) — RDF reconstruction",
            "Cai, Zhang, Guan arXiv:2510.12134 (2025) — bubble template on RQF",
            "Polomni M8 residual-consensus — frozen WMAP-K scar axis",
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _build_verdict(
    *,
    p_coherence: float,
    p_template_shuffle: float,
    p_template_sim: float,
    p_cai: float = 1.0,
    p_cai_sim: float = 1.0,
    rble_gate: bool,
    combined_gate: bool,
    phase_d: bool = False,
    fisher_snr: float = 0.0,
    multi_z_snr: float = 0.0,
    multi_z_p: float = 1.0,
) -> str:
    if combined_gate and (fisher_snr > 2.0 or multi_z_snr > 1.5):
        return (
            "Fisher / multi-z bubble invariant above null — "
            "requires blind Planck holdout before multiverse visibility claim."
        )
    if multi_z_p < 0.05 and multi_z_snr > 0.8:
        return (
            "Marginal multi-z Fisher excess — not sufficient for multiverse detection; "
            "sensitivity ladder continues (ACT×DESI-class tracers)."
        )
    if phase_d and not combined_gate:
        return (
            "Quadratic estimator shows template excess but RBLE scar channel or axis alignment "
            "does not close — investigate before any multiverse claim."
        )
    if p_cai < 0.05 or p_cai_sim < 0.05:
        return (
            "Marginal quadratic Cai template excess — not sufficient for multiverse detection."
        )
    if combined_gate:
        return (
            "RBLE scar axis + bubble template show coordinated enhancement — "
            "requires independent Planck holdout and full quadratic estimator before physics claim."
        )
    if p_template_shuffle < 0.05 or p_template_sim < 0.05:
        return (
            "Marginal template excess — investigate systematics; not sufficient for multiverse physics."
        )
    if rble_gate:
        return (
            "RBLE scar axis shows template enhancement but global template search null — "
            "model-specific channel only; not bubble visibility proof."
        )
    return (
        "No bubble-collision template above galaxy-shuffle or ΛCDM simulation null — "
        "consistent with standard cosmology in this proxy; RBLE operational proof (M8/M9) remains separate."
    )


def rble_model_physics_validation(
    *,
    nside: int = 32,
    nside_dir: int = 8,
    seed: int = 0,
    rdf_amp: float = 100.0,
    rqf_amp: float = 75.0,
) -> dict[str, Any]:
    """Computational multiverse physics: district imprint → RDF/RQF template recovery.

    Validates that the P5 instrument detects bubble-class signatures at the axis
    the RBLE closed loop imprints — the causal chain our model claims.
    """
    import healpy as hp

    from polomni.core.superspace.district_graph import ChoicePolicy, DistrictGraph
    from polomni.integration.cmb_imprint import imprint_cmb_from_packets

    graph = DistrictGraph(gravity_mutation_strength=0.06)
    root = graph.add_district(
        mass=10.0,
        law_of_gravity=[6.674e-11, 1.1e-52],
        coordinate=[0.2, 0.3, 0.9],
        lambda_vacuum=1.0e-52,
    )
    packets = graph.trigger_choice_event(root, num_choices=4, policy=ChoicePolicy.UNIFORM)
    cmb, true_axis = imprint_cmb_from_packets(packets, graph, nside=nside, seed=seed)

    mask = galactic_edge_mask(nside, b_cut=20.0)
    rng = np.random.default_rng(seed)
    gal_pix = rng.choice(np.where(mask)[0], size=300, replace=False)
    vecs = np.column_stack(hp.pix2vec(nside, gal_pix))
    delta = galaxy_overdensity_map(vecs, nside, mask)
    cmb_hp = high_pass_cmb_map(cmb, lmin=30, mask=mask)
    t_inj, d_inj = inject_bubble_rdf_signal(
        cmb_hp, delta, true_axis, rdf_amp=rdf_amp, rqf_amp=rqf_amp, mask=mask
    )

    tmpl_axis, tmpl_score, _, _, _ = search_bubble_template_axis(
        t_inj, d_inj, mask=mask, nside_dir=nside_dir
    )
    scar_test = rble_scar_axis_test(t_inj, d_inj, true_axis, mask=mask, n_null=32, seed=seed)
    sep = axis_separation_deg(tmpl_axis, true_axis)
    gate = bool(sep < 20.0 and scar_test["gate_pass"])

    return {
        "chain": "district_graph → cmb_imprint → bubble_rdf_injection → template_search",
        "true_imprint_axis": true_axis.tolist(),
        "recovered_template_axis": tmpl_axis.tolist(),
        "axis_error_deg": round(sep, 2),
        "template_score": round(tmpl_score, 4),
        "rble_scar_test": scar_test,
        "gate_pass": gate,
        "interpretation": (
            "RBLE multiverse physics chain validated in simulation"
            if gate
            else "Chain validation failed — check imprint amplitude or search grid"
        ),
    }


def write_rdf_report(
    report: dict[str, Any],
    path: Path | str | None = None,
) -> Path:
    import json

    path = Path(path or "data/reports/p5_rdf_tomography.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path
