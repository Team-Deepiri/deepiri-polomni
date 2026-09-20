"""Phase L — DESI LRG × fixed-axis matched-filter (J×K locksmith lever).

SOTA: Cai et al. arXiv:2510.12134 — SO(2,1) m=0 + tomography; ACT×DESI LRG
already used for RDF reconstruction. Phase K showed Pearson Fisher does not
scale with DESI N. Phase J unblocked the estimator — apply it on DESI shells
at the frozen RBLE axis (no sky-max LEE).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.sources.amplitude_locksmith import (
    fixed_axis_matched_report,
    inject_amplitude_ladder,
)
from polomni.observatory.pipeline.sources.bubble_collisions import (
    galactic_edge_mask,
    load_planck_for_search,
)
from polomni.observatory.pipeline.sources.desi_lrg_tracer import (
    DEFAULT_Z_EDGES,
    desi_z_bins,
    load_desi_lrg_galactic,
)
from polomni.observatory.pipeline.sources.iras_pscz import load_pscz_catalog
from polomni.observatory.pipeline.sources.sky_frames import equatorial_to_galactic


def desi_amplitude_locksmith_report(
    *,
    nside: int = 64,
    lmin: int = 30,
    b_cut: float = 20.0,
    n_null: int = 24,
    seed: int = 0,
    cache: DataCache | None = None,
    refresh: bool = False,
    z_edges: tuple[float, ...] = DEFAULT_Z_EDGES,
) -> dict[str, Any]:
    """Phase L: fixed-axis MF on DESI LRG (+ multi-z shells) vs PSCz baseline."""
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
    if scar is None:
        scar = np.array([0.0, 0.0, 1.0], dtype=float)

    delta_d = galaxy_overdensity_map(desi["vecs_gal"], nside, mask)
    delta_p = galaxy_overdensity_map(pscz_gal, nside, mask)

    fixed_desi = fixed_axis_matched_report(
        cmb_hp,
        delta_d,
        mask,
        scar,
        n_null=n_null,
        seed=seed,
        galaxy_vecs=desi["vecs_gal"],
    )
    fixed_pscz = fixed_axis_matched_report(
        cmb_hp,
        delta_p,
        mask,
        scar,
        n_null=max(12, n_null // 2),
        seed=seed + 1,
        galaxy_vecs=pscz_gal,
    )

    bins = desi_z_bins(desi["z"], desi["vecs_gal"], z_edges=z_edges)
    bin_rows: list[dict[str, Any]] = []
    zs: list[float] = []
    ws: list[float] = []
    for i, b in enumerate(bins):
        if b["n_galaxies"] < 500:
            bin_rows.append(
                {
                    "z_lo": b["z_lo"],
                    "z_hi": b["z_hi"],
                    "n_galaxies": b["n_galaxies"],
                    "skipped": True,
                }
            )
            continue
        d_bin = galaxy_overdensity_map(b["vecs_gal"], nside, mask)
        rep = fixed_axis_matched_report(
            cmb_hp,
            d_bin,
            mask,
            scar,
            n_null=max(12, n_null // 2),
            seed=seed + 10 + i,
            galaxy_vecs=b["vecs_gal"],
        )
        ez = float((rep.get("observed") or {}).get("excess_z", 0.0))
        nr = float((rep.get("observed") or {}).get("null_ratio", 0.0))
        bin_rows.append(
            {
                "z_lo": b["z_lo"],
                "z_hi": b["z_hi"],
                "z_mid": b["z_mid"],
                "n_galaxies": b["n_galaxies"],
                "kernel_weight": round(b["kernel_weight"], 4),
                "excess_z": round(ez, 4),
                "null_ratio": round(nr, 4),
                "fisher_snr": (rep.get("observed") or {}).get("fisher_snr"),
                "p_value": (rep.get("null") or {}).get("p_value"),
                "gate_pass": bool(rep.get("gate_pass")),
                "skipped": False,
            }
        )
        zs.append(ez)
        ws.append(float(b["kernel_weight"]))

    stacked_z = 0.0
    if ws and zs:
        w = np.asarray(ws, dtype=float)
        w = w / (w.sum() + 1e-15)
        stacked_z = float(np.dot(w, np.asarray(zs, dtype=float)))

    ladder = inject_amplitude_ladder(
        cmb_hp,
        delta_d,
        mask,
        scar,
        amplitudes=(2.0, 4.0, 8.0, 16.0),
        n_null=max(12, n_null // 2),
        seed=seed + 50,
        galaxy_vecs=desi["vecs_gal"],
    )

    z_d = float((fixed_desi.get("observed") or {}).get("excess_z", 0.0))
    z_p = float((fixed_pscz.get("observed") or {}).get("excess_z", 0.0))
    r_d = float((fixed_desi.get("observed") or {}).get("null_ratio", 0.0))
    r_p = float((fixed_pscz.get("observed") or {}).get("null_ratio", 0.0))
    gate = bool(fixed_desi.get("gate_pass")) or any(
        bool(b.get("gate_pass")) for b in bin_rows if not b.get("skipped")
    )
    path_proven = bool(ladder.get("amplitude_path_proven"))

    return {
        "phase": "L_desi_amplitude_locksmith",
        "sota_refs": [
            "Cai, Zhang, Guan arXiv:2510.12134",
            "Phase J matched-filter + Phase K DESI Guadalupe LRG",
        ],
        "map_product_id": pid,
        "scar_axis_gal": scar.tolist(),
        "tracer_desi": {
            "n_galaxies": desi["n_galaxies"],
            "z_range": desi["z_range"],
            "sources": desi["sources"],
        },
        "matched_fixed_desi": fixed_desi,
        "matched_fixed_pscz": fixed_pscz,
        "multi_z_matched": {
            "z_edges": list(z_edges),
            "bins": bin_rows,
            "stacked_excess_z": round(stacked_z, 4),
        },
        "inject_ladder_desi": ladder,
        "scaling": {
            "excess_z_desi": round(z_d, 4),
            "excess_z_pscz": round(z_p, 4),
            "null_ratio_desi": round(r_d, 4),
            "null_ratio_pscz": round(r_p, 4),
            "stacked_excess_z": round(stacked_z, 4),
            "beats_pscz_excess": bool(z_d > z_p or stacked_z > z_p),
            "min_inject_amp_gate": ladder.get("min_amp_gate_pass"),
            "amplitude_path_proven": path_proven,
        },
        "gate_pass": gate,
        "interpretation": (
            "DESI×MF GATE PASS — bubble_visible candidate on fixed-axis matched-filter"
            if gate
            else (
                f"DESI fixed-axis excess_z={z_d:.2f} (PSCz {z_p:.2f}) "
                f"stack={stacked_z:.2f} null_ratio={r_d:.2f}; "
                f"inject Amin={ladder.get('min_amp_gate_pass')} "
                f"path_proven={path_proven}. Keep hammering."
            )
        ),
    }
