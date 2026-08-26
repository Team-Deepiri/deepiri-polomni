"""Phase K — DESI LRG Fisher (Guadalupe public clustering) + Cai multi-z.

SOTA math (Cai, Zhang, Guan arXiv:2510.12134):
- Bubble collision SO(2,1) ⇒ Fisher on m=0 RDF/RQF template [A,B]
- Tomography across Z_e bins mitigates ΛCDM variance (optimistic path)
- ACT×DESI LRG already demonstrated for RDF reconstruction

Lever: replace SDSS SpecObj strips with real DESI LRG (N≈2.6e5 Guadalupe).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.sources.bubble_collisions import (
    galactic_edge_mask,
    load_planck_for_search,
)
from polomni.observatory.pipeline.sources.dense_tracer import forecast_fisher_snr
from polomni.observatory.pipeline.sources.desi_lrg_tracer import (
    DEFAULT_Z_EDGES,
    desi_z_bins,
    load_desi_lrg_galactic,
)
from polomni.observatory.pipeline.sources.iras_pscz import load_pscz_catalog
from polomni.observatory.pipeline.sources.multiverse_fisher_scan import fisher_scan_report
from polomni.observatory.pipeline.sources.quadratic_remote_field import (
    _unit,
    axis_separation_deg,
)
from polomni.observatory.pipeline.sources.sky_frames import equatorial_to_galactic


def desi_lrg_fisher_report(
    *,
    nside: int = 64,
    lmin: int = 30,
    b_cut: float = 20.0,
    nside_dir: int = 8,
    n_null: int = 16,
    seed: int = 0,
    cache: DataCache | None = None,
    refresh: bool = False,
    z_edges: tuple[float, ...] = DEFAULT_Z_EDGES,
) -> dict[str, Any]:
    """Phase K: Planck × DESI LRG Fisher + multi-z coherence + PSCz baseline."""
    from polomni.observatory.pipeline.sources.rdf_tomography import (
        galaxy_overdensity_map,
        high_pass_cmb_map,
        load_rble_scar_axis,
    )

    cache = cache or DataCache()
    desi = load_desi_lrg_galactic(cache=cache, refresh=refresh, with_pscz=False)
    pscz = load_pscz_catalog()
    pscz_gal = equatorial_to_galactic(pscz["vecs_eq"])

    mask = galactic_edge_mask(nside, b_cut=b_cut)
    cmb, pid = load_planck_for_search(
        map_product_id="planck_smica_cmb", nside=nside, cache=cache
    )
    cmb_hp = high_pass_cmb_map(cmb, lmin=lmin, mask=mask)
    scar = load_rble_scar_axis()
    f_sky = float(np.mean(mask))

    delta_d = galaxy_overdensity_map(desi["vecs_gal"], nside, mask)
    delta_p = galaxy_overdensity_map(pscz_gal, nside, mask)

    fisher_d = fisher_scan_report(
        cmb_hp,
        delta_d,
        mask,
        nside_dir=nside_dir,
        n_null=n_null,
        seed=seed,
        scar_axis=scar,
    )
    fisher_p = fisher_scan_report(
        cmb_hp,
        delta_p,
        mask,
        nside_dir=max(4, nside_dir // 2),
        n_null=max(4, n_null // 2),
        seed=seed + 1,
        scar_axis=scar,
    )

    # Multi-z Cai tomography on DESI shells
    bins = desi_z_bins(desi["z"], desi["vecs_gal"], z_edges=z_edges)
    bin_rows: list[dict[str, Any]] = []
    axes: list[np.ndarray] = []
    snrs: list[float] = []
    weights: list[float] = []
    for i, b in enumerate(bins):
        if b["n_galaxies"] < 200:
            bin_rows.append({**{k: b[k] for k in ("z_lo", "z_hi", "z_mid", "n_galaxies", "kernel_weight")}, "skipped": True})
            continue
        d_bin = galaxy_overdensity_map(b["vecs_gal"], nside, mask)
        scan = fisher_scan_report(
            cmb_hp,
            d_bin,
            mask,
            nside_dir=max(4, nside_dir // 2),
            n_null=max(4, n_null // 2),
            seed=seed + 10 + i,
            scar_axis=scar,
        )
        snr = float((scan.get("observed") or {}).get("fisher_snr", 0.0))
        ax = np.asarray((scan.get("observed") or {}).get("best_axis_gal") or [0, 0, 1], dtype=float)
        bin_rows.append(
            {
                "z_lo": b["z_lo"],
                "z_hi": b["z_hi"],
                "z_mid": b["z_mid"],
                "n_galaxies": b["n_galaxies"],
                "kernel_weight": round(b["kernel_weight"], 4),
                "fisher_snr": round(snr, 4),
                "p_value": (scan.get("null") or {}).get("p_value"),
                "best_axis_gal": ax.tolist(),
                "skipped": False,
            }
        )
        axes.append(_unit(ax))
        snrs.append(snr)
        weights.append(float(b["kernel_weight"]))

    stacked_snr = 0.0
    coherence_deg: float | None = None
    if weights and snrs:
        w = np.asarray(weights, dtype=float)
        w = w / (w.sum() + 1e-15)
        stacked_snr = float(np.dot(w, np.asarray(snrs, dtype=float)))
        seps: list[float] = []
        for i in range(len(axes)):
            for j in range(i + 1, len(axes)):
                seps.append(axis_separation_deg(axes[i], axes[j]))
        coherence_deg = float(np.mean(seps)) if seps else None

    snr_d = float((fisher_d.get("observed") or {}).get("fisher_snr", 0.0))
    snr_p = float((fisher_p.get("observed") or {}).get("fisher_snr", 0.0))
    n_d = int(desi["n_galaxies"])
    n_p = int(pscz_gal.shape[0])
    expected = float(np.sqrt(n_d / max(n_p, 1)))
    observed = snr_d / max(abs(snr_p), 1e-6)
    forecast = forecast_fisher_snr(
        max(snr_d, stacked_snr, snr_p),
        n_gal_now=n_d,
        f_sky_now=f_sky,
        n_gal_future=2.0e6,  # full DR1-class LRG
        f_sky_future=0.35,
    )
    multi_z_gate = bool(
        stacked_snr > 2.0
        and coherence_deg is not None
        and coherence_deg < 35.0
        and all(
            (r.get("p_value") is not None and float(r["p_value"]) < 0.05)
            for r in bin_rows
            if not r.get("skipped")
        )
    )
    gate = bool(fisher_d.get("gate_pass") or multi_z_gate)

    return {
        "phase": "K_desi_lrg_fisher",
        "sota_refs": [
            "Cai, Zhang, Guan arXiv:2510.12134 (RDF/RQF bubble SO(2,1) + tomography)",
            "DESI Guadalupe LSS clustering VAC (Ross et al. / DESI Data docs)",
        ],
        "map_product_id": pid,
        "tracer_desi": {
            "n_galaxies": n_d,
            "counts": desi["counts"],
            "sources": desi["sources"],
            "z_range": desi["z_range"],
            "files": desi["files"],
        },
        "fisher_desi": fisher_d,
        "fisher_pscz_baseline": {
            "fisher_snr": round(snr_p, 4),
            "p_value": (fisher_p.get("null") or {}).get("p_value"),
            "n_galaxies": n_p,
        },
        "multi_z": {
            "z_edges": list(z_edges),
            "bins": bin_rows,
            "stacked_snr": round(stacked_snr, 4),
            "cross_z_mean_sep_deg": round(coherence_deg, 2) if coherence_deg is not None else None,
            "gate_pass": multi_z_gate,
        },
        "scaling": {
            "snr_desi": round(snr_d, 4),
            "snr_pscz": round(snr_p, 4),
            "snr_multi_z_stack": round(stacked_snr, 4),
            "n_ratio": round(n_d / max(n_p, 1), 4),
            "expected_snr_ratio_sqrt_n": round(expected, 4),
            "observed_snr_ratio": round(observed, 4),
            "beats_pscz": bool(snr_d > snr_p or stacked_snr > snr_p),
            "sqrt_n_scaling_holds": bool(observed >= 0.5 * expected),
        },
        "forecast_full_dr1_lrg": forecast,
        "gate_pass": gate,
        "interpretation": (
            "DESI LRG GATE PASS — bubble_visible candidate; confirm holdout + prereg"
            if gate
            else (
                f"DESI N={n_d} SNR={snr_d:.2f} multi-z={stacked_snr:.2f} "
                f"vs PSCz {snr_p:.2f} (√N exp {expected:.1f}×, obs {observed:.2f}×); "
                f"full-DR1 forecast {forecast['snr_forecast']:.1f}. "
                "Visibility not ruled out."
            )
        ),
    }
