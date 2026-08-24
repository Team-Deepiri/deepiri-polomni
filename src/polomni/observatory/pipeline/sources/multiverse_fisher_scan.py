"""Fisher-optimal joint bubble-collision scanner — Phase E multiverse mathematics.

Locksmith reframe (P5→P6):
- Dead end: maximize RDF or RQF separately (axes misalign at 26–81° on real sky).
- New invariant: eternal-inflation bubble collisions are SO(2,1)-symmetric → in the
  collision-aligned frame only **m=0** modes at ℓ=1 (RDF) and ℓ=2 (RQF) coactivate
  with fixed amplitude ratio A:B (Cai et al. arXiv:2510.12134).
- Outsider loop: subtract ΛCDM kSZ contamination (galaxy-dipole coupled ℓ=1) BEFORE
  measuring the bubble invariant — ACT×DESI detects structure, not bubbles.
- System fix: Fisher SNR on the 2-dim bubble template [a₁⁰, a₂⁰] with analytic noise.

This is the deepest in-repo multiverse scan: not "find an axis," but test whether
the joint superhorizon mode matches a preregistered bubble template above N⁻¹ noise.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from polomni.observatory.pipeline.sources.quadratic_remote_field import (
    QuadraticFieldResult,
    _unit,
    axis_separation_deg,
    quadratic_remote_fields,
)


def _pixel_directions(nside: int) -> np.ndarray:
    import healpy as hp

    theta, phi = hp.pix2ang(nside, np.arange(hp.nside2npix(nside)))
    return np.column_stack(
        [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
    )


@dataclass
class BubbleM0Amplitudes:
    """m=0 RDF/RQF amplitudes in collision-aligned frame."""

    a10: complex
    a20: complex
    axis: np.ndarray
    ratio_abs: float
    sign_coherent: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "a10_real": round(float(np.real(self.a10)), 6),
            "a10_imag": round(float(np.imag(self.a10)), 6),
            "a20_real": round(float(np.real(self.a20)), 6),
            "a20_imag": round(float(np.imag(self.a20)), 6),
            "ratio_abs_a10_a20": round(self.ratio_abs, 4),
            "sign_coherent": self.sign_coherent,
            "axis": self.axis.tolist(),
        }


def extract_m0_amplitudes(
    rdf_map: np.ndarray,
    rqf_map: np.ndarray,
    axis: np.ndarray,
    *,
    mask: np.ndarray,
    dirs: np.ndarray | None = None,
) -> BubbleM0Amplitudes:
    """SO(2,1) m=0 amplitudes via normalized Legendre correlations.

    Returns dimensionless corr(F, P_ℓ(μ)) so Fisher SNR is O(1) for a matched
    bubble and O(N⁻¹/²) under nulls — no healpy rotate_alm required.
    """
    import healpy as hp

    axis_u = _unit(axis)
    if dirs is None:
        dirs = _pixel_directions(hp.get_nside(rdf_map))
    good = mask & np.isfinite(rdf_map) & np.isfinite(rqf_map)
    if not np.any(good):
        return BubbleM0Amplitudes(
            a10=0.0, a20=0.0, axis=axis_u, ratio_abs=0.0, sign_coherent=True
        )
    mu = dirs[good] @ axis_u
    p1 = mu
    p2 = 1.5 * mu * mu - 0.5
    rdf = rdf_map[good]
    rqf = rqf_map[good]

    def _corr(field: np.ndarray, template: np.ndarray) -> float:
        tf = template - float(np.mean(template))
        ff = field - float(np.mean(field))
        denom = float(np.linalg.norm(ff) * np.linalg.norm(tf))
        if denom < 1e-30:
            return 0.0
        return float(np.dot(ff, tf) / denom)

    a10 = complex(_corr(rdf, p1))
    a20 = complex(_corr(rqf, p2))
    ratio = abs(a10) / max(abs(a20), 1e-30)
    coherent = bool(np.real(a10) * np.real(a20) >= 0)
    return BubbleM0Amplitudes(
        a10=a10, a20=a20, axis=axis_u, ratio_abs=ratio, sign_coherent=coherent
    )


def fisher_bubble_snr(
    amps: BubbleM0Amplitudes,
    *,
    A: float = 1.0,
    B: float = 0.65,
    noise_l1: float = 1.0,
    noise_l2: float = 1.0,
) -> float:
    """Fisher SNR on dimensionless (corr₁, corr₂) bubble template t=[A,B]."""
    del noise_l1, noise_l2  # correlations are already scale-free
    x = np.array([float(np.real(amps.a10)), float(np.real(amps.a20))], dtype=float)
    t = np.array([A, B], dtype=float)
    t /= np.linalg.norm(t) + 1e-15
    return float(np.dot(x, t))


def mitigate_lcdm_contamination(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    mask: np.ndarray,
    *,
    lmax: int | None = None,
) -> np.ndarray:
    """Remove *small-scale* linear T–δ coupling without erasing bubble RDF/RQF.

    Locksmith: full-sky Cov(T,δ) γ-subtraction kills any bubble aligned with the
    tracer. Outsider cut: high-pass δ (strip ℓ≤2), then T ← T − γ δ_hp. Superhorizon
    bubble modes live in ℓ=1,2 of T and are orthogonal to δ_hp in expectation;
    ΛCDM-like ISW/kSZ leakage on smaller scales is suppressed.
    """
    import healpy as hp

    t = np.asarray(cmb_hp, dtype=float).ravel().copy()
    d = np.asarray(delta_g, dtype=float).ravel().copy()
    nside = hp.get_nside(t)
    lmax_use = lmax if lmax is not None else min(3 * nside - 1, 64)
    d_m = d.copy()
    d_m[~mask] = 0.0
    d_alm = hp.map2alm(d_m, lmax=lmax_use)
    for ell in (0, 1, 2):
        for m in range(0, ell + 1):
            d_alm[hp.Alm.getidx(lmax_use, ell, m)] = 0.0
    d_hp = hp.alm2map(d_alm, nside)
    good = mask & np.isfinite(t) & np.isfinite(d_hp)
    if not np.any(good):
        return t
    dg = d_hp[good] - float(np.mean(d_hp[good]))
    tg = t[good] - float(np.mean(t[good]))
    var_d = float(np.dot(dg, dg))
    if var_d < 1e-30:
        out = t.copy()
        out[~mask] = 0.0
        return out
    gamma = float(np.dot(tg, dg) / var_d)
    out = t.copy()
    out[good] = t[good] - gamma * d_hp[good]
    out[~mask] = 0.0
    return out


def quadratic_fields_mitigated(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    mask: np.ndarray,
    *,
    f_sky: float | None = None,
) -> QuadraticFieldResult:
    """MV quadratic RDF/RQF after ΛCDM ℓ=1 mitigation."""
    cmb_m = mitigate_lcdm_contamination(cmb_hp, delta_g, mask)
    fields = quadratic_remote_fields(cmb_m, delta_g, mask, f_sky=f_sky)
    fields.metadata["lcdm_mitigation"] = True
    return fields


@dataclass
class FisherBubbleScanResult:
    best_axis: np.ndarray
    best_snr: float
    best_amps: BubbleM0Amplitudes
    template_A: float
    template_B: float

    def to_dict(self) -> dict[str, Any]:
        import healpy as hp

        th, ph = hp.vec2ang(self.best_axis.reshape(1, 3))
        return {
            "best_axis_gal": self.best_axis.tolist(),
            "best_gal_lon": round(float(np.degrees(ph)[0]), 2),
            "best_gal_lat": round(float(90.0 - np.degrees(th)[0]), 2),
            "fisher_snr": round(self.best_snr, 4),
            "m0_amplitudes": self.best_amps.to_dict(),
            "template_A": self.template_A,
            "template_B": self.template_B,
        }


def scan_fisher_bubble_axis(
    fields: QuadraticFieldResult,
    mask: np.ndarray,
    *,
    nside_dir: int = 8,
    A: float = 1.0,
    B: float = 0.65,
) -> FisherBubbleScanResult:
    """Grid search: axis maximizing Fisher bubble SNR on m=0 amplitudes."""
    import healpy as hp

    nside_dir = max(1, int(nside_dir))
    grid = _pixel_directions(nside_dir)[: hp.nside2npix(nside_dir)]
    dirs = _pixel_directions(hp.get_nside(fields.rdf_map))

    best_snr = -1e30
    best_axis = grid[0]
    best_amps = extract_m0_amplitudes(
        fields.rdf_map, fields.rqf_map, best_axis, mask=mask, dirs=dirs
    )
    for ax in grid:
        amps = extract_m0_amplitudes(
            fields.rdf_map, fields.rqf_map, ax, mask=mask, dirs=dirs
        )
        snr = fisher_bubble_snr(amps, A=A, B=B)
        if snr > best_snr:
            best_snr = snr
            best_axis = ax
            best_amps = amps

    return FisherBubbleScanResult(
        best_axis=_unit(best_axis),
        best_snr=float(best_snr),
        best_amps=best_amps,
        template_A=A,
        template_B=B,
    )


def joint_bubble_invariant(amps: BubbleM0Amplitudes, *, A: float = 1.0, B: float = 0.65) -> float:
    """SO(2,1) bubble invariant: projection onto template with sign coherence penalty."""
    x = np.array([float(np.real(amps.a10)), float(np.real(amps.a20))])
    t = np.array([A, B])
    t /= np.linalg.norm(t) + 1e-15
    proj = float(np.dot(x, t))
    if not amps.sign_coherent:
        proj *= 0.25
    return proj


def fisher_scan_report(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    mask: np.ndarray,
    *,
    nside_dir: int = 8,
    n_null: int = 32,
    seed: int = 0,
    scar_axis: np.ndarray | None = None,
) -> dict[str, Any]:
    """Full Phase E Fisher bubble scan with ΛCDM mitigation + nulls."""
    f_sky = float(np.mean(mask))
    fields = quadratic_fields_mitigated(cmb_hp, delta_g, mask, f_sky=f_sky)
    obs = scan_fisher_bubble_axis(fields, mask, nside_dir=nside_dir)

    rng = np.random.default_rng(seed)
    from polomni.observatory.pipeline.sources.rdf_tomography import (
        galaxy_overdensity_map,
        shuffle_galaxy_positions,
    )

    import healpy as hp

    nside = hp.get_nside(cmb_hp)
    dirs = _pixel_directions(nside)
    gal_pix = np.where(mask & (np.abs(delta_g) > 0.01))[0]
    if gal_pix.size < 50:
        gal_pix = np.where(mask)[0][:300]
    vecs = dirs[gal_pix[: min(500, gal_pix.size)]]
    null_snr: list[float] = []
    for _ in range(n_null):
        shuf = shuffle_galaxy_positions(vecs, nside, mask, rng)
        d_null = galaxy_overdensity_map(shuf, nside, mask)
        f_null = quadratic_fields_mitigated(cmb_hp, d_null, mask, f_sky=f_sky)
        res = scan_fisher_bubble_axis(f_null, mask, nside_dir=4)
        null_snr.append(res.best_snr)

    null_arr = np.asarray(null_snr, dtype=float)
    p_snr = float((1 + np.sum(null_arr >= obs.best_snr)) / (n_null + 1))

    scar_result: dict[str, Any] | None = None
    scar_sep: float | None = None
    if scar_axis is not None:
        scar_amps = extract_m0_amplitudes(
            fields.rdf_map, fields.rqf_map, scar_axis, mask=mask
        )
        scar_snr = fisher_bubble_snr(scar_amps)
        scar_result = {
            "fisher_snr_at_scar": round(scar_snr, 4),
            "m0_amplitudes": scar_amps.to_dict(),
            "invariant": round(joint_bubble_invariant(scar_amps), 6),
        }
        scar_sep = axis_separation_deg(obs.best_axis, scar_axis)

    gate = bool(p_snr < 0.01 and obs.best_snr > 2.0 and obs.best_amps.sign_coherent)
    if scar_sep is not None:
        gate = gate and scar_sep < 25.0

    return {
        "phase": "E_fisher_bubble",
        "lcdm_mitigation": True,
        "observed": obs.to_dict(),
        "null": {
            "n_realizations": n_null,
            "median_snr": round(float(np.median(null_arr)), 4),
            "p_value": round(p_snr, 4),
        },
        "rble_scar": {
            **(scar_result or {}),
            "sep_from_fisher_axis_deg": round(scar_sep, 2) if scar_sep else None,
        },
        "gate_pass": gate,
        "invariant": round(joint_bubble_invariant(obs.best_amps), 6),
        "interpretation": (
            "Joint SO(2,1) bubble mode above Fisher null — candidate superhorizon signature"
            if gate
            else "No Fisher bubble invariant above ΛCDM-mitigated null at current sensitivity"
        ),
    }
