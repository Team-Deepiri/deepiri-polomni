"""Phase G — blind Fisher holdout: freeze axis on WMAP, test on Planck.

Locksmith reframe (P7→P8):
- Dead end: maximize Fisher on Planck, then claim detection (look-elsewhere + peeking).
- New question: does the **WMAP-frozen** bubble axis still show Fisher excess on
  **independent** Planck×PSCz? That is the visibility bar without circularity.
- Outsider loop: we already cache wmap_k_band + planck_smica; no new survey required.
- System fix: preregistered train/test map IDs + single-axis holdout SNR (no grid max
  on the test map).

Gate: holdout p_snr < 0.01 at frozen axis, holdout SNR > 1.0, optional free-search
WMAP↔Planck axis sep < 35° (consistency, not used for selection).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.sources.bubble_collisions import (
    galactic_edge_mask,
    load_planck_for_search,
)
from polomni.observatory.pipeline.sources.multiverse_fisher_scan import (
    extract_m0_amplitudes,
    fisher_bubble_snr,
    quadratic_fields_mitigated,
    scan_fisher_bubble_axis,
)
from polomni.observatory.pipeline.sources.quadratic_remote_field import (
    _unit,
    axis_separation_deg,
)


TRAIN_MAP_ID = "wmap_k_band"
TEST_MAP_ID = "planck_smica_cmb"


def fisher_snr_at_axis(
    cmb_hp: np.ndarray,
    delta_g: np.ndarray,
    mask: np.ndarray,
    axis: np.ndarray,
    *,
    A: float = 1.0,
    B: float = 0.65,
) -> float:
    """Fisher bubble SNR at a **frozen** axis (no grid search — holdout-safe)."""
    f_sky = float(np.mean(mask))
    fields = quadratic_fields_mitigated(cmb_hp, delta_g, mask, f_sky=f_sky)
    amps = extract_m0_amplitudes(fields.rdf_map, fields.rqf_map, axis, mask=mask)
    return fisher_bubble_snr(amps, A=A, B=B)


def blind_fisher_holdout_report(
    vecs_gal: np.ndarray,
    *,
    nside: int = 64,
    lmin: int = 30,
    b_cut: float = 20.0,
    nside_dir_train: int = 8,
    n_null: int = 16,
    seed: int = 0,
    train_map_id: str = TRAIN_MAP_ID,
    test_map_id: str = TEST_MAP_ID,
    cache: DataCache | None = None,
    A: float = 1.0,
    B: float = 0.65,
) -> dict[str, Any]:
    """Train Fisher axis on WMAP; evaluate SNR at that axis on Planck (blind)."""
    from polomni.observatory.pipeline.sources.rdf_tomography import (
        galaxy_overdensity_map,
        high_pass_cmb_map,
        shuffle_galaxy_positions,
    )
    import healpy as hp

    cache = cache or DataCache()
    mask = galactic_edge_mask(nside, b_cut=b_cut)
    delta_g = galaxy_overdensity_map(vecs_gal, nside, mask)

    train_raw, train_pid = load_planck_for_search(
        map_product_id=train_map_id, nside=nside, cache=cache
    )
    test_raw, test_pid = load_planck_for_search(
        map_product_id=test_map_id, nside=nside, cache=cache
    )
    train_hp = high_pass_cmb_map(train_raw, lmin=lmin, mask=mask)
    test_hp = high_pass_cmb_map(test_raw, lmin=lmin, mask=mask)

    # --- TRAIN: free Fisher axis search on WMAP (axis selection only) ---
    f_sky = float(np.mean(mask))
    train_fields = quadratic_fields_mitigated(train_hp, delta_g, mask, f_sky=f_sky)
    train_scan = scan_fisher_bubble_axis(
        train_fields, mask, nside_dir=nside_dir_train, A=A, B=B
    )
    frozen_axis = _unit(train_scan.best_axis)
    train_snr = float(train_scan.best_snr)

    # --- TEST: SNR only at frozen axis on Planck (no re-maximization) ---
    holdout_snr = fisher_snr_at_axis(test_hp, delta_g, mask, frozen_axis, A=A, B=B)

    # Free Planck search for consistency check only (not used in gate selection)
    test_fields = quadratic_fields_mitigated(test_hp, delta_g, mask, f_sky=f_sky)
    test_free = scan_fisher_bubble_axis(
        test_fields, mask, nside_dir=max(4, nside_dir_train // 2), A=A, B=B
    )
    free_sep = axis_separation_deg(frozen_axis, test_free.best_axis)

    # Nulls: shuffle galaxies; measure Planck SNR at the *same frozen* axis
    rng = np.random.default_rng(seed)
    dirs = np.column_stack(
        hp.pix2vec(nside, np.arange(hp.nside2npix(nside)))
    )
    gal_pix = np.where(mask & (np.abs(delta_g) > 0.01))[0]
    if gal_pix.size < 50:
        gal_pix = np.where(mask)[0][:300]
    base_vecs = dirs[gal_pix[: min(500, gal_pix.size)]]
    null_snr: list[float] = []
    for _ in range(n_null):
        shuf = shuffle_galaxy_positions(base_vecs, nside, mask, rng)
        d_null = galaxy_overdensity_map(shuf, nside, mask)
        null_snr.append(
            fisher_snr_at_axis(test_hp, d_null, mask, frozen_axis, A=A, B=B)
        )
    null_arr = np.asarray(null_snr, dtype=float)
    p_hold = float((1 + np.sum(null_arr >= holdout_snr)) / (n_null + 1))

    th, ph = hp.vec2ang(frozen_axis.reshape(1, 3))
    gate = bool(p_hold < 0.01 and holdout_snr > 1.0 and train_snr > 0.5)

    return {
        "phase": "G_blind_fisher_holdout",
        "protocol": {
            "train_map": train_pid,
            "test_map": test_pid,
            "axis_selection": "Fisher max on train only",
            "holdout_statistic": "Fisher SNR at frozen axis on test (no grid max)",
        },
        "train": {
            "fisher_snr": round(train_snr, 4),
            "frozen_axis_gal": frozen_axis.tolist(),
            "gal_lon": round(float(np.degrees(ph)[0]), 2),
            "gal_lat": round(float(90.0 - np.degrees(th)[0]), 2),
            "sign_coherent": train_scan.best_amps.sign_coherent,
        },
        "holdout": {
            "fisher_snr_at_frozen_axis": round(holdout_snr, 4),
            "null": {
                "n_realizations": n_null,
                "median_snr": round(float(np.median(null_arr)), 4),
                "p_value": round(p_hold, 4),
            },
        },
        "consistency": {
            "planck_free_search_snr": round(float(test_free.best_snr), 4),
            "wmap_planck_free_axis_sep_deg": round(free_sep, 2),
            "note": "Free Planck search is diagnostic only — not used for gate",
        },
        "gate_pass": gate,
        "interpretation": (
            "WMAP-frozen Fisher axis exceeds Planck holdout null — candidate for "
            "bubble_visible after denser-tracer confirmation"
            if gate
            else "Blind WMAP→Planck Fisher holdout null at current sensitivity — "
            "multiverse not ruled out; need denser tracers / more nulls"
        ),
    }
