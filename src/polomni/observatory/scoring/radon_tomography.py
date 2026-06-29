"""Geodesic Radon tomography on S² — Eq. 6 RBLE signature from real line integrals.

Implements the observatory definition from CMB_OBSERVATORY_MATH.md:

    S_RBLE(n̂) = ∫₀^{2π} |R_{S²}[T ⊗ W_string](n̂, η)| dη

with optional bifurcation weighting |R''(η)| from the WDW closure (Eq. 3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from polomni.core.radon.transform_s2 import radon_transform_s2
from polomni.observatory.filters.string_filter import string_landscape_filter
from polomni.observatory.ingest.healpix_loader import map_nside

DEFAULT_W_PARAMS: dict[str, Any] = {
    "W0": 0.0,
    "beta": 0.15,
    "modes": [{"amplitude": 1.0, "m": 2, "n": 1, "phase": 0.0}],
}


@dataclass(frozen=True)
class RadonTomogram:
    """Full geodesic Radon slice through a CMB map at axis n̂."""

    n_hat: np.ndarray
    eta: np.ndarray
    profile: np.ndarray
    bifurcation: np.ndarray
    score_integral: float
    score_bifurcation: float
    score_contrast: float
    te_conductance: np.ndarray | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "n_hat": self.n_hat.tolist(),
            "eta": self.eta.tolist(),
            "profile": self.profile.tolist(),
            "bifurcation": self.bifurcation.tolist(),
            "score_integral": self.score_integral,
            "score_bifurcation": self.score_bifurcation,
            "score_contrast": self.score_contrast,
        }
        if self.te_conductance is not None:
            out["te_conductance"] = self.te_conductance.tolist()
        return out


def _unit(n_hat: np.ndarray) -> np.ndarray:
    v = np.asarray(n_hat, dtype=float).ravel()
    return v / (np.linalg.norm(v) + 1e-15)


def _prepare_map(
    healpix_map: np.ndarray,
    *,
    apply_string_filter: bool,
    W_params: dict[str, Any] | None,
) -> np.ndarray:
    f = np.asarray(healpix_map, dtype=float).ravel()
    if not apply_string_filter:
        return f
    params = W_params if W_params is not None else DEFAULT_W_PARAMS
    return string_landscape_filter(f, params)


def geodesic_radon_profile(
    healpix_map: np.ndarray,
    n_hat: np.ndarray,
    *,
    n_eta: int = 128,
    method: Literal["transform", "pixel"] = "transform",
) -> tuple[np.ndarray, np.ndarray]:
    """Sample R_{S²}[f](n̂, η) on η ∈ [0, 2π)."""
    n = _unit(n_hat)
    nside = map_nside(healpix_map)
    eta = np.linspace(0.0, 2.0 * np.pi, n_eta, endpoint=False)

    if method == "pixel":
        from polomni.observatory.filters.radon_bifurcation import _radon_profile_s2

        profile = _radon_profile_s2(healpix_map, n, n_eta=n_eta)
        return profile, eta

    profile = np.array(
        [radon_transform_s2(healpix_map, n, float(e), nside=nside) for e in eta],
        dtype=float,
    )
    return profile, eta


def bifurcation_spectrum(profile: np.ndarray) -> np.ndarray:
    """|R''(η)| — WDW bifurcation emphasis along the geodesic."""
    p = np.asarray(profile, dtype=float)
    d2 = np.gradient(np.gradient(p))
    return np.abs(d2)


def scores_from_profile(profile: np.ndarray) -> tuple[float, float, float]:
    """Integral, bifurcation, and RMS contrast scores from one Radon profile."""
    p = np.asarray(profile, dtype=float)
    d_eta = 2.0 * np.pi / max(len(p), 1)
    integral = float(np.sum(np.abs(p)) * d_eta)
    bif = float(np.sum(bifurcation_spectrum(p)) * d_eta)
    contrast = float(np.std(p) / (np.mean(np.abs(p)) + 1e-12))
    return integral, bif, contrast


def te_conductance_along_geodesic(
    t_map: np.ndarray,
    q_map: np.ndarray,
    u_map: np.ndarray,
    n_hat: np.ndarray,
    *,
    n_eta: int = 64,
    window: float = 0.12,
) -> np.ndarray:
    """M(η): local T–E coupling along geodesic arc segments (Eq. 6 polarization term)."""
    try:
        import healpy as hp
    except ImportError:
        return np.zeros(n_eta)

    n = _unit(n_hat)
    nside = map_nside(t_map)
    t_map = np.asarray(t_map, dtype=float).ravel()
    q_map = np.asarray(q_map, dtype=float).ravel()
    u_map = np.asarray(u_map, dtype=float).ravel()
    e_proxy = np.sqrt(q_map**2 + u_map**2)

    eta = np.linspace(0.0, 2.0 * np.pi, n_eta, endpoint=False)
    tangent = np.cross(n, np.array([0.0, 0.0, 1.0]))
    if np.linalg.norm(tangent) < 1e-8:
        tangent = np.cross(n, np.array([0.0, 1.0, 0.0]))
    tangent /= np.linalg.norm(tangent) + 1e-15

    conductance = np.zeros(n_eta, dtype=float)
    for i, angle in enumerate(eta):
        pt = np.cos(angle) * n + np.sin(angle) * tangent
        pt /= np.linalg.norm(pt)
        theta, phi = hp.vec2ang(pt)
        ring_t: list[float] = []
        ring_e: list[float] = []
        for dphi in np.linspace(-window, window, 9):
            ipix = hp.ang2pix(nside, theta, phi + dphi)
            ring_t.append(float(t_map[ipix]))
            ring_e.append(float(e_proxy[ipix]))
        if len(ring_t) < 3:
            continue
        rt, re = np.asarray(ring_t), np.asarray(ring_e)
        if np.std(rt) < 1e-15 or np.std(re) < 1e-15:
            continue
        conductance[i] = float(np.corrcoef(rt, re)[0, 1])
    return conductance


def build_radon_tomogram(
    healpix_map: np.ndarray,
    n_hat: np.ndarray,
    *,
    n_eta: int = 128,
    apply_string_filter: bool = True,
    W_params: dict[str, Any] | None = None,
    q_map: np.ndarray | None = None,
    u_map: np.ndarray | None = None,
    method: Literal["transform", "pixel"] = "transform",
) -> RadonTomogram:
    """Full tomographic slice at axis n̂ with scores and optional TE conductance."""
    filtered = _prepare_map(
        healpix_map,
        apply_string_filter=apply_string_filter,
        W_params=W_params,
    )
    profile, eta = geodesic_radon_profile(filtered, n_hat, n_eta=n_eta, method=method)
    bif = bifurcation_spectrum(profile)
    integral, bif_score, contrast = scores_from_profile(profile)

    te_cond = None
    if q_map is not None and u_map is not None:
        te_cond = te_conductance_along_geodesic(
            filtered,
            q_map,
            u_map,
            n_hat,
            n_eta=min(n_eta, 64),
        )

    return RadonTomogram(
        n_hat=_unit(n_hat),
        eta=eta,
        profile=profile,
        bifurcation=bif,
        score_integral=integral,
        score_bifurcation=bif_score,
        score_contrast=contrast,
        te_conductance=te_cond,
    )


def rble_score_at_axis(
    healpix_map: np.ndarray,
    n_hat: np.ndarray,
    *,
    weight: Literal["integral", "bifurcation", "contrast"] = "integral",
    n_eta: int = 64,
    apply_string_filter: bool = True,
    W_params: dict[str, Any] | None = None,
    method: Literal["transform", "pixel"] = "pixel",
) -> float:
    """Scalar S_RBLE(n̂) for one axis (fast pixel method default for search)."""
    filtered = _prepare_map(
        healpix_map,
        apply_string_filter=apply_string_filter,
        W_params=W_params,
    )
    profile, _ = geodesic_radon_profile(filtered, n_hat, n_eta=n_eta, method=method)
    integral, bif, contrast = scores_from_profile(profile)
    if weight == "bifurcation":
        return bif
    if weight == "contrast":
        return contrast
    return integral


def rble_axis_landscape(
    healpix_map: np.ndarray,
    *,
    nside_dirs: int = 8,
    n_eta: int = 32,
    apply_string_filter: bool = True,
    W_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Coarse S_RBLE(n̂) over HEALPix pixel directions — the Radon scar landscape on S²."""
    import healpy as hp

    filtered = _prepare_map(
        healpix_map,
        apply_string_filter=apply_string_filter,
        W_params=W_params,
    )
    npix = hp.nside2npix(nside_dirs)
    ipix = np.arange(npix)
    theta, phi = hp.pix2ang(nside_dirs, ipix)
    x = np.column_stack(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
    )

    scores: list[float] = []
    for direction in x:
        s = rble_score_at_axis(
            filtered,
            direction,
            n_eta=n_eta,
            apply_string_filter=False,
            method="pixel",
        )
        scores.append(s)

    scores_arr = np.asarray(scores, dtype=float)
    peak_idx = int(np.argmax(scores_arr))
    lon = np.degrees(phi)
    lat = 90.0 - np.degrees(theta)

    return {
        "nside_dirs": nside_dirs,
        "lon": lon.tolist(),
        "lat": lat.tolist(),
        "scores": scores_arr.tolist(),
        "peak_axis": x[peak_idx].tolist(),
        "peak_score": float(scores_arr[peak_idx]),
        "score_mean": float(np.mean(scores_arr)),
        "score_std": float(np.std(scores_arr)),
    }


def fingerprint_bifurcation_peaks(bifurcation: np.ndarray, eta: np.ndarray, *, top_k: int = 5) -> list[dict[str, float]]:
    """Novel bifurcation fingerprint: peak locations and amplitudes along η."""
    b = np.asarray(bifurcation, dtype=float)
    e = np.asarray(eta, dtype=float)
    if b.size == 0:
        return []
    order = np.argsort(b)[::-1][:top_k]
    return [
        {"eta_rad": float(e[i]), "eta_deg": float(np.degrees(e[i])), "amplitude": float(b[i])}
        for i in order
        if b[i] > 0
    ]
