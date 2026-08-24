"""Minimum-variance quadratic RDF/RQF estimator (Deutsch et al. PRD 98, 123501).

Reconstructs remote dipole (RDF) and quadrupole (RQF) fields from small-scale
CMB temperature × galaxy overdensity, following the kSZ/pSZ tomography formalism
used in Cai–Zhang–Guan (arXiv:2510.12134) and ACT×DESI analyses.

This is a harmonic-space MV estimator (single redshift bin). Full tomography with
multiple bins and SZ_cosmo kernels is future work; this module is the production
step beyond the Phase A pixel-weighted proxy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class QuadraticFieldResult:
    """Reconstructed RDF/RQF maps and low-multipole alms."""

    rdf_map: np.ndarray
    rqf_map: np.ndarray
    rdf_alm: np.ndarray
    rqf_alm: np.ndarray
    dipole_axis: np.ndarray
    quadrupole_axis: np.ndarray
    axis_separation_deg: float
    lmax: int
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        import healpy as hp

        def _lonlat(v: np.ndarray) -> tuple[float, float]:
            th, ph = hp.vec2ang(v.reshape(1, 3))
            return float(np.degrees(ph)[0]), float(90.0 - np.degrees(th)[0])

        d_lon, d_lat = _lonlat(self.dipole_axis)
        q_lon, q_lat = _lonlat(self.quadrupole_axis)
        return {
            "dipole_axis": self.dipole_axis.tolist(),
            "dipole_gal_lon": round(d_lon, 2),
            "dipole_gal_lat": round(d_lat, 2),
            "quadrupole_axis": self.quadrupole_axis.tolist(),
            "quadrupole_gal_lon": round(q_lon, 2),
            "quadrupole_gal_lat": round(q_lat, 2),
            "axis_separation_deg": round(self.axis_separation_deg, 2),
            "lmax": self.lmax,
            "metadata": self.metadata,
        }


def _pixel_directions(nside: int) -> np.ndarray:
    import healpy as hp

    theta, phi = hp.pix2ang(nside, np.arange(hp.nside2npix(nside)))
    return np.column_stack(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
    )


def _unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float).reshape(3)
    n = float(np.linalg.norm(v))
    if n < 1e-15:
        return np.array([0.0, 0.0, 1.0])
    return v / n


def _alm_extract_multipole(alm: np.ndarray, lmax: int, ell: int) -> np.ndarray:
    """Zero all alm except one multipole."""
    import healpy as hp

    out = np.zeros_like(alm)
    for m in range(-ell, ell + 1):
        idx = hp.Alm.getidx(lmax, ell, m)
        out[idx] = alm[idx]
    return out


def mv_noise_at_l(t_cl: np.ndarray, g_cl: np.ndarray, ell: int, f_sky: float) -> float:
    """Scale-independent reconstruction noise (Bloch & Johnson 2024 limit)."""
    if ell >= len(t_cl) or ell >= len(g_cl):
        return 1.0
    n_l = float(t_cl[ell] * g_cl[ell]) / max(2 * ell + 1, 1)
    return max(n_l / max(f_sky, 0.1), 1e-30)


def dipole_axis_from_map(field: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Dipole vector Σ_p F(p) n̂_p on the masked sky."""
    import healpy as hp

    f = np.asarray(field, dtype=float).ravel()
    nside = hp.get_nside(f)
    dirs = _pixel_directions(nside)
    w = f * mask
    vec = dirs.T @ w
    return _unit(vec)


def quadrupole_axis_from_map(field: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Principal symmetry axis from quadrupole tensor of field * n̂ n̂^T."""
    import healpy as hp

    f = np.asarray(field, dtype=float).ravel()
    nside = hp.get_nside(f)
    dirs = _pixel_directions(nside)
    good = mask & np.isfinite(f)
    if not np.any(good):
        return np.array([0.0, 0.0, 1.0])
    d = dirs[good]
    w = f[good]
    q = np.einsum("pi,p,pj->ij", d, w, d) / max(np.sum(np.abs(w)), 1e-15)
    evals, evecs = np.linalg.eigh(q)
    return _unit(evecs[:, int(np.argmax(evals))])


def axis_separation_deg(a: np.ndarray, b: np.ndarray) -> float:
    dot = float(np.clip(np.abs(np.dot(_unit(a), _unit(b))), 0.0, 1.0))
    return float(np.degrees(np.arccos(dot)))


def quadratic_remote_fields(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    mask: np.ndarray,
    *,
    lmax: int | None = None,
    f_sky: float | None = None,
) -> QuadraticFieldResult:
    """MV quadratic RDF (ℓ=1) and RQF (ℓ=2) reconstruction maps."""
    import healpy as hp

    t = np.asarray(cmb_hp, dtype=float).ravel().copy()
    d = np.asarray(delta_g, dtype=float).ravel().copy()
    nside = hp.get_nside(t)
    if d.shape != t.shape or mask.shape != t.shape:
        raise ValueError("cmb_hp, delta_g, mask must share nside")

    lmax = lmax if lmax is not None else min(3 * nside - 1, 128)
    lmax = max(lmax, 2)
    f_sky = float(np.mean(mask)) if f_sky is None else f_sky

    t_m = t.copy()
    d_m = d.copy()
    t_m[~mask] = 0.0
    d_m[~mask] = 0.0

    chi = t_m * d_m
    chi_alm = hp.map2alm(chi, lmax=lmax)
    t_cl = hp.alm2cl(hp.map2alm(t_m, lmax=lmax))
    g_cl = hp.alm2cl(hp.map2alm(d_m, lmax=lmax))

    rdf_alm = np.zeros_like(chi_alm)
    rqf_alm = np.zeros_like(chi_alm)
    for ell, target in ((1, rdf_alm), (2, rqf_alm)):
        n_l = mv_noise_at_l(t_cl, g_cl, ell, f_sky)
        w_l = 1.0 / n_l
        for m in range(-ell, ell + 1):
            idx = hp.Alm.getidx(lmax, ell, m)
            target[idx] = chi_alm[idx] * w_l

    rdf_only = _alm_extract_multipole(rdf_alm, lmax, 1)
    rqf_only = _alm_extract_multipole(rqf_alm, lmax, 2)
    rdf_map = hp.alm2map(rdf_only, nside)
    rqf_map = hp.alm2map(rqf_only, nside)
    rdf_map[~mask] = 0.0
    rqf_map[~mask] = 0.0

    dip_axis = dipole_axis_from_map(rdf_map, mask)
    quad_axis = quadrupole_axis_from_map(rqf_map, mask)
    sep = axis_separation_deg(dip_axis, quad_axis)

    return QuadraticFieldResult(
        rdf_map=rdf_map,
        rqf_map=rqf_map,
        rdf_alm=rdf_only,
        rqf_alm=rqf_only,
        dipole_axis=dip_axis,
        quadrupole_axis=quad_axis,
        axis_separation_deg=sep,
        lmax=lmax,
        metadata={
            "estimator": "MV quadratic (Deutsch et al. 2018, single-z bin)",
            "f_sky": round(f_sky, 4),
            "noise_l1": round(mv_noise_at_l(t_cl, g_cl, 1, f_sky), 6),
            "noise_l2": round(mv_noise_at_l(t_cl, g_cl, 2, f_sky), 6),
        },
    )


def inject_quadratic_signal(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    axis: np.ndarray,
    *,
    rdf_amp: float = 8.0,
    rqf_amp: float = 5.0,
    mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Plant MV-detectable RDF+RQF signal for validation."""
    import healpy as hp

    nside = hp.get_nside(cmb_hp)
    dirs = _pixel_directions(nside)
    axis_u = _unit(axis)
    mu = dirs @ axis_u
    t_inj = rdf_amp * mu + rqf_amp * 0.5 * (3.0 * mu * mu - 1.0)
    d_inj = 0.4 * rdf_amp * mu + 0.4 * rqf_amp * 0.5 * (3.0 * mu * mu - 1.0)
    t_out = np.asarray(cmb_hp, dtype=float) + t_inj
    d_out = np.asarray(delta_g, dtype=float) + d_inj
    if mask is not None:
        t_out = t_out.copy()
        d_out = d_out.copy()
        t_out[~mask] = 0.0
        d_out[~mask] = 0.0
    return t_out, d_out
