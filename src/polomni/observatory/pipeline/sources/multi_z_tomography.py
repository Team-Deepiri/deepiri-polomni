"""Phase F — multi-z RemoteField-style tomography on PSCz redshift shells.

Locksmith reframe (P6→P7):
- Dead end: single-z Planck×PSCz Fisher SNR ~1.3, p~0.08 (sensitivity floor).
- New invariant: a true SO(2,1) bubble axis is **the same across redshift shells**;
  ΛCDM kSZ leakage and shot noise do not share a fixed axis through z.
- Outsider loop: PSCz already ships Hvel → z; no RemoteField vendor clone required.
- System fix: kernel-weighted stack of per-bin Fisher vectors + cross-z axis coherence.

Kernel: w(z) ∝ √N_bin · K_RDF(z) with K_RDF ≈ z e^{-z/z_*} (Deutsch/Cai-style
radial weight proxy). Stacked SNR = ŵ · mean_z(x_z); coherence = mean pairwise
axis separation across bins (small → candidate bubble).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from polomni.observatory.pipeline.sources.multiverse_fisher_scan import (
    BubbleM0Amplitudes,
    extract_m0_amplitudes,
    joint_bubble_invariant,
    quadratic_fields_mitigated,
    scan_fisher_bubble_axis,
)
from polomni.observatory.pipeline.sources.quadratic_remote_field import (
    _unit,
    axis_separation_deg,
)

# Default cz shells covering PSCz (z≈0–0.1): nearby / mid / far
DEFAULT_Z_EDGES: tuple[float, ...] = (0.0, 0.012, 0.035, 0.12)
Z_STAR = 0.04  # RDF kernel scale (proxy; RemoteField uses full transfer)


def redshift_kernel_weight(z_mid: float, n_gal: int, *, z_star: float = Z_STAR) -> float:
    """Radial kernel weight √N · z exp(-z/z_*)."""
    z = max(float(z_mid), 1e-6)
    k = z * np.exp(-z / max(z_star, 1e-6))
    return float(np.sqrt(max(n_gal, 1)) * k)


def assign_z_bins(
    z: np.ndarray,
    edges: Sequence[float] = DEFAULT_Z_EDGES,
) -> list[np.ndarray]:
    """Boolean masks for galaxies in each [z_lo, z_hi) shell."""
    z = np.asarray(z, dtype=float)
    masks: list[np.ndarray] = []
    for i in range(len(edges) - 1):
        lo, hi = float(edges[i]), float(edges[i + 1])
        masks.append(np.isfinite(z) & (z >= lo) & (z < hi))
    return masks


@dataclass
class ZBinFisherResult:
    z_lo: float
    z_hi: float
    z_mid: float
    n_gal: int
    weight: float
    best_axis: np.ndarray
    fisher_snr: float
    sign_coherent: bool
    corr1: float
    corr2: float

    def to_dict(self) -> dict[str, Any]:
        import healpy as hp

        th, ph = hp.vec2ang(self.best_axis.reshape(1, 3))
        return {
            "z_lo": self.z_lo,
            "z_hi": self.z_hi,
            "z_mid": round(self.z_mid, 5),
            "n_gal": self.n_gal,
            "kernel_weight": round(self.weight, 4),
            "fisher_snr": round(self.fisher_snr, 4),
            "sign_coherent": self.sign_coherent,
            "corr1": round(self.corr1, 4),
            "corr2": round(self.corr2, 4),
            "best_axis_gal": self.best_axis.tolist(),
            "best_gal_lon": round(float(np.degrees(ph)[0]), 2),
            "best_gal_lat": round(float(90.0 - np.degrees(th)[0]), 2),
        }


def mean_pairwise_axis_sep_deg(axes: Sequence[np.ndarray]) -> float:
    """Mean pairwise axis separation (deg) — small ⇒ coherent across z."""
    if len(axes) < 2:
        return 0.0
    seps: list[float] = []
    for i in range(len(axes)):
        for j in range(i + 1, len(axes)):
            seps.append(axis_separation_deg(axes[i], axes[j]))
    return float(np.mean(seps)) if seps else 0.0


def stack_fisher_vector(
    bin_results: Sequence[ZBinFisherResult],
    *,
    A: float = 1.0,
    B: float = 0.65,
) -> tuple[float, np.ndarray, bool]:
    """Kernel-weighted mean of (corr1, corr2); return stacked SNR, axis, coherence."""
    if not bin_results:
        return 0.0, np.array([0.0, 0.0, 1.0]), True
    w = np.asarray([b.weight for b in bin_results], dtype=float)
    w = w / (np.sum(w) + 1e-15)
    x = np.asarray([[b.corr1, b.corr2] for b in bin_results], dtype=float)
    x_bar = w @ x
    t = np.array([A, B], dtype=float)
    t /= np.linalg.norm(t) + 1e-15
    snr = float(np.dot(x_bar, t))
    axes = np.asarray([b.best_axis for b in bin_results], dtype=float)
    ref = axes[0]
    for i in range(1, len(axes)):
        if float(np.dot(axes[i], ref)) < 0:
            axes[i] = -axes[i]
    stacked_axis = _unit(w @ axes)
    coherent = all(b.sign_coherent for b in bin_results)
    return snr, stacked_axis, coherent


def _amps_from_stack(bins: Sequence[ZBinFisherResult]) -> BubbleM0Amplitudes:
    w = np.asarray([b.weight for b in bins], dtype=float)
    w = w / (np.sum(w) + 1e-15)
    x = w @ np.asarray([[b.corr1, b.corr2] for b in bins], dtype=float)
    return BubbleM0Amplitudes(
        a10=complex(float(x[0])),
        a20=complex(float(x[1])),
        axis=_unit(bins[0].best_axis),
        ratio_abs=abs(x[0]) / max(abs(x[1]), 1e-30),
        sign_coherent=all(b.sign_coherent for b in bins),
    )


def run_z_bin_fisher(
    cmb_hp: np.ndarray,
    vecs_gal: np.ndarray,
    mask: np.ndarray,
    bin_mask: np.ndarray,
    *,
    z_lo: float,
    z_hi: float,
    nside_dir: int = 8,
    A: float = 1.0,
    B: float = 0.65,
) -> ZBinFisherResult | None:
    """Fisher bubble scan on one redshift shell (skip if too few galaxies)."""
    from polomni.observatory.pipeline.sources.rdf_tomography import galaxy_overdensity_map
    import healpy as hp

    n_gal = int(np.sum(bin_mask))
    if n_gal < 80:
        return None
    delta = galaxy_overdensity_map(vecs_gal[bin_mask], hp.get_nside(cmb_hp), mask)
    f_sky = float(np.mean(mask))
    fields = quadratic_fields_mitigated(cmb_hp, delta, mask, f_sky=f_sky)
    scan = scan_fisher_bubble_axis(fields, mask, nside_dir=nside_dir, A=A, B=B)
    z_mid = 0.5 * (z_lo + z_hi)
    w = redshift_kernel_weight(z_mid, n_gal)
    return ZBinFisherResult(
        z_lo=z_lo,
        z_hi=z_hi,
        z_mid=z_mid,
        n_gal=n_gal,
        weight=w,
        best_axis=scan.best_axis,
        fisher_snr=scan.best_snr,
        sign_coherent=scan.best_amps.sign_coherent,
        corr1=float(np.real(scan.best_amps.a10)),
        corr2=float(np.real(scan.best_amps.a20)),
    )


def multi_z_fisher_report(
    cmb_hp: np.ndarray,
    vecs_gal: np.ndarray,
    z: np.ndarray,
    mask: np.ndarray,
    *,
    z_edges: Sequence[float] = DEFAULT_Z_EDGES,
    nside_dir: int = 8,
    n_null: int = 16,
    seed: int = 0,
    scar_axis: np.ndarray | None = None,
    A: float = 1.0,
    B: float = 0.65,
) -> dict[str, Any]:
    """Phase F: multi-z kernel-weighted Fisher + cross-z axis coherence + nulls."""
    from polomni.observatory.pipeline.sources.rdf_tomography import (
        galaxy_overdensity_map,
        shuffle_galaxy_positions,
    )
    import healpy as hp

    edges = tuple(float(e) for e in z_edges)
    bin_masks = assign_z_bins(z, edges)
    bins: list[ZBinFisherResult] = []
    for i, bm in enumerate(bin_masks):
        res = run_z_bin_fisher(
            cmb_hp,
            vecs_gal,
            mask,
            bm,
            z_lo=edges[i],
            z_hi=edges[i + 1],
            nside_dir=nside_dir,
            A=A,
            B=B,
        )
        if res is not None:
            bins.append(res)

    if not bins:
        return {
            "phase": "F_multi_z_tomography",
            "gate_pass": False,
            "bins": [],
            "interpretation": "Insufficient galaxies per redshift shell for multi-z Fisher",
        }

    stacked_snr, stacked_axis, sign_ok = stack_fisher_vector(bins, A=A, B=B)
    axis_coh_deg = mean_pairwise_axis_sep_deg([b.best_axis for b in bins])

    rng = np.random.default_rng(seed)
    nside = hp.get_nside(cmb_hp)
    null_snr: list[float] = []
    null_coh: list[float] = []
    for _ in range(n_null):
        shuf = shuffle_galaxy_positions(vecs_gal, nside, mask, rng)
        null_bins: list[ZBinFisherResult] = []
        for i, bm in enumerate(bin_masks):
            if int(np.sum(bm)) < 80:
                continue
            idx = np.where(bm)[0]
            sub = shuf[idx]
            delta = galaxy_overdensity_map(sub, nside, mask)
            fields = quadratic_fields_mitigated(
                cmb_hp, delta, mask, f_sky=float(np.mean(mask))
            )
            scan = scan_fisher_bubble_axis(fields, mask, nside_dir=4, A=A, B=B)
            z_mid = 0.5 * (edges[i] + edges[i + 1])
            null_bins.append(
                ZBinFisherResult(
                    z_lo=edges[i],
                    z_hi=edges[i + 1],
                    z_mid=z_mid,
                    n_gal=int(idx.size),
                    weight=redshift_kernel_weight(z_mid, int(idx.size)),
                    best_axis=scan.best_axis,
                    fisher_snr=scan.best_snr,
                    sign_coherent=scan.best_amps.sign_coherent,
                    corr1=float(np.real(scan.best_amps.a10)),
                    corr2=float(np.real(scan.best_amps.a20)),
                )
            )
        if not null_bins:
            continue
        ns, _, _ = stack_fisher_vector(null_bins, A=A, B=B)
        null_snr.append(ns)
        null_coh.append(mean_pairwise_axis_sep_deg([b.best_axis for b in null_bins]))

    null_snr_arr = np.asarray(null_snr, dtype=float) if null_snr else np.array([0.0])
    null_coh_arr = np.asarray(null_coh, dtype=float) if null_coh else np.array([90.0])
    p_snr = float((1 + np.sum(null_snr_arr >= stacked_snr)) / (len(null_snr_arr) + 1))
    p_coh = float((1 + np.sum(null_coh_arr <= axis_coh_deg)) / (len(null_coh_arr) + 1))

    scar_block: dict[str, Any] = {}
    if scar_axis is not None:
        scar_sep = axis_separation_deg(stacked_axis, scar_axis)
        corr_at_scar: list[tuple[float, float, float]] = []
        for b in bins:
            bm = np.isfinite(z) & (z >= b.z_lo) & (z < b.z_hi)
            if int(np.sum(bm)) < 80:
                continue
            delta = galaxy_overdensity_map(vecs_gal[bm], nside, mask)
            fields = quadratic_fields_mitigated(
                cmb_hp, delta, mask, f_sky=float(np.mean(mask))
            )
            amps = extract_m0_amplitudes(
                fields.rdf_map, fields.rqf_map, scar_axis, mask=mask
            )
            corr_at_scar.append(
                (b.weight, float(np.real(amps.a10)), float(np.real(amps.a20)))
            )
        if corr_at_scar:
            ww = np.asarray([c[0] for c in corr_at_scar], dtype=float)
            ww = ww / (np.sum(ww) + 1e-15)
            x = np.asarray([[c[1], c[2]] for c in corr_at_scar], dtype=float)
            t = np.array([A, B], dtype=float)
            t /= np.linalg.norm(t) + 1e-15
            scar_snr = float(np.dot(ww @ x, t))
        else:
            scar_snr = 0.0
        scar_block = {
            "sep_from_stacked_axis_deg": round(scar_sep, 2),
            "fisher_snr_at_scar": round(scar_snr, 4),
        }

    gate = bool(
        p_snr < 0.01
        and stacked_snr > 1.5
        and sign_ok
        and axis_coh_deg < 35.0
        and p_coh < 0.05
    )
    if scar_block.get("sep_from_stacked_axis_deg") is not None:
        gate = gate and float(scar_block["sep_from_stacked_axis_deg"]) < 25.0

    th, ph = hp.vec2ang(stacked_axis.reshape(1, 3))
    stacked_amps = _amps_from_stack(bins)
    return {
        "phase": "F_multi_z_tomography",
        "z_edges": list(edges),
        "n_bins_used": len(bins),
        "bins": [b.to_dict() for b in bins],
        "stacked": {
            "fisher_snr": round(stacked_snr, 4),
            "sign_coherent_all_bins": sign_ok,
            "axis_gal": stacked_axis.tolist(),
            "gal_lon": round(float(np.degrees(ph)[0]), 2),
            "gal_lat": round(float(90.0 - np.degrees(th)[0]), 2),
            "mean_pairwise_axis_sep_deg": round(axis_coh_deg, 2),
            "invariant": round(joint_bubble_invariant(stacked_amps, A=A, B=B), 6),
        },
        "null": {
            "n_realizations": len(null_snr_arr),
            "median_snr": round(float(np.median(null_snr_arr)), 4),
            "p_value_snr": round(p_snr, 4),
            "median_axis_sep_deg": round(float(np.median(null_coh_arr)), 2),
            "p_value_coherence": round(p_coh, 4),
        },
        "rble_scar": scar_block,
        "gate_pass": gate,
        "interpretation": (
            "Multi-z Fisher stack + cross-z axis coherence above null — candidate bubble"
            if gate
            else "No multi-z bubble invariant above null at current PSCz×Planck sensitivity"
        ),
    }
