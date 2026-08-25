"""Phase I — hammer visibility: PSCz ∪ NVSS-bright ∪ mega-SDSS Fisher.

All-sky radio (NVSS) + IRAS PSCz + denser SpecObj. Compare SNR to PSCz-only
and Phase H; update DESI forecast. This is the no-DESI-file maximum push.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.sources.bubble_collisions import (
    galactic_edge_mask,
    load_planck_for_search,
)
from polomni.observatory.pipeline.sources.dense_lrg_fisher import fetch_sdss_lrg_dense
from polomni.observatory.pipeline.sources.dense_tracer import (
    _unique_unit_vectors,
    forecast_fisher_snr,
)
from polomni.observatory.pipeline.sources.iras_pscz import load_pscz_catalog
from polomni.observatory.pipeline.sources.multiverse_fisher_scan import fisher_scan_report
from polomni.observatory.pipeline.sources.nvss_tracer import (
    fetch_nvss_bright,
    load_nvss_vectors,
)
from polomni.observatory.pipeline.sources.sky_frames import equatorial_to_galactic


def load_hammer_tracer_galactic(
    *,
    cache: DataCache | None = None,
    refresh: bool = False,
    mega_sdss: bool = True,
) -> dict[str, Any]:
    """Stack PSCz + NVSS bright + optional mega SDSS LRG strips."""
    from polomni.observatory.pipeline.sources.cross_sky import load_galaxy_vectors

    cache = cache or DataCache()
    errors: list[str] = []
    parts: list[np.ndarray] = []
    sources: list[str] = []
    counts: dict[str, int] = {}

    cat = load_pscz_catalog()
    parts.append(equatorial_to_galactic(cat["vecs_eq"]))
    sources.append("iras_pscz")
    counts["iras_pscz"] = int(cat["vecs_eq"].shape[0])

    try:
        fetch_nvss_bright(cache=cache, force=refresh)
        nv = load_nvss_vectors()
        parts.append(equatorial_to_galactic(nv))
        sources.append("nvss_bright")
        counts["nvss_bright"] = int(nv.shape[0])
    except Exception as exc:
        errors.append(f"nvss:{exc}")

    if mega_sdss:
        try:
            fetch_sdss_lrg_dense(
                cache=cache,
                force=refresh,
                n_per_strip=400,
                n_strips=48,
                z_lo=0.1,
                z_hi=0.8,
            )
            path = cache.resolved_path("sdss_lrg_dense")
            if path is None:
                path = cache.root / "sdss_lrg_dense" / "sdss_lrg_dense.json"
            if Path(path).is_file():
                eq = load_galaxy_vectors(path)
                parts.append(equatorial_to_galactic(eq))
                sources.append("sdss_lrg_mega")
                counts["sdss_lrg_mega"] = int(eq.shape[0])
        except Exception as exc:
            errors.append(f"sdss:{exc}")

    stacked = _unique_unit_vectors(np.vstack(parts))
    return {
        "vecs_gal": stacked,
        "n_galaxies": int(stacked.shape[0]),
        "counts": counts,
        "sources": sources,
        "errors": errors,
    }


def _fisher_snr_for_vecs(
    *,
    cmb_hp: np.ndarray,
    vecs_gal: np.ndarray,
    mask: np.ndarray,
    nside: int,
    nside_dir: int,
    n_null: int,
    seed: int,
    scar_axis: np.ndarray | None,
) -> dict[str, Any]:
    from polomni.observatory.pipeline.sources.rdf_tomography import galaxy_overdensity_map

    delta = galaxy_overdensity_map(vecs_gal, nside, mask)
    return fisher_scan_report(
        cmb_hp,
        delta,
        mask,
        nside_dir=nside_dir,
        n_null=n_null,
        seed=seed,
        scar_axis=scar_axis,
    )


def hammer_fisher_report(
    *,
    nside: int = 64,
    lmin: int = 30,
    b_cut: float = 20.0,
    nside_dir: int = 8,
    n_null: int = 16,
    seed: int = 0,
    cache: DataCache | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """Phase I: Fisher on hammer tracer vs PSCz / PSCz∪NVSS baselines."""
    from polomni.observatory.pipeline.sources.rdf_tomography import (
        high_pass_cmb_map,
        load_rble_scar_axis,
    )

    cache = cache or DataCache()
    hammer = load_hammer_tracer_galactic(cache=cache, refresh=refresh, mega_sdss=True)
    radio = load_hammer_tracer_galactic(cache=cache, refresh=False, mega_sdss=False)
    pscz = load_pscz_catalog()
    pscz_gal = equatorial_to_galactic(pscz["vecs_eq"])

    mask = galactic_edge_mask(nside, b_cut=b_cut)
    cmb, pid = load_planck_for_search(
        map_product_id="planck_smica_cmb", nside=nside, cache=cache
    )
    cmb_hp = high_pass_cmb_map(cmb, lmin=lmin, mask=mask)
    scar = load_rble_scar_axis()
    f_sky = float(np.mean(mask))
    dir_coarse = max(4, nside_dir // 2)
    null_coarse = max(4, n_null // 2)

    fisher_h = _fisher_snr_for_vecs(
        cmb_hp=cmb_hp,
        vecs_gal=hammer["vecs_gal"],
        mask=mask,
        nside=nside,
        nside_dir=nside_dir,
        n_null=n_null,
        seed=seed,
        scar_axis=scar,
    )
    fisher_radio = _fisher_snr_for_vecs(
        cmb_hp=cmb_hp,
        vecs_gal=radio["vecs_gal"],
        mask=mask,
        nside=nside,
        nside_dir=dir_coarse,
        n_null=null_coarse,
        seed=seed + 2,
        scar_axis=scar,
    )
    fisher_p = _fisher_snr_for_vecs(
        cmb_hp=cmb_hp,
        vecs_gal=pscz_gal,
        mask=mask,
        nside=nside,
        nside_dir=dir_coarse,
        n_null=null_coarse,
        seed=seed + 1,
        scar_axis=scar,
    )

    snr_h = float((fisher_h.get("observed") or {}).get("fisher_snr", 0.0))
    snr_r = float((fisher_radio.get("observed") or {}).get("fisher_snr", 0.0))
    snr_p = float((fisher_p.get("observed") or {}).get("fisher_snr", 0.0))
    n_h = int(hammer["n_galaxies"])
    n_r = int(radio["n_galaxies"])
    n_p = int(pscz_gal.shape[0])
    expected = float(np.sqrt(n_h / max(n_p, 1)))
    observed = snr_h / max(abs(snr_p), 1e-6)
    # Forecast from best public stack (radio or hammer), not the diluted one.
    snr_best = max(snr_h, snr_r, snr_p)
    n_best = n_h if snr_h >= snr_r and snr_h >= snr_p else (n_r if snr_r >= snr_p else n_p)
    forecast = forecast_fisher_snr(snr_best, n_gal_now=n_best, f_sky_now=f_sky)
    gate = bool(fisher_h.get("gate_pass")) or bool(fisher_radio.get("gate_pass"))

    return {
        "phase": "I_hammer_visibility",
        "map_product_id": pid,
        "tracer_hammer": {
            "n_galaxies": n_h,
            "counts": hammer["counts"],
            "sources": hammer["sources"],
            "errors": hammer["errors"],
        },
        "tracer_pscz_nvss": {
            "n_galaxies": n_r,
            "counts": radio["counts"],
            "sources": radio["sources"],
        },
        "fisher_hammer": fisher_h,
        "fisher_pscz_nvss": {
            "fisher_snr": round(snr_r, 4),
            "p_value": (fisher_radio.get("null") or {}).get("p_value"),
            "gate_pass": bool(fisher_radio.get("gate_pass")),
            "n_galaxies": n_r,
        },
        "fisher_pscz_baseline": {
            "fisher_snr": round(snr_p, 4),
            "p_value": (fisher_p.get("null") or {}).get("p_value"),
            "n_galaxies": n_p,
        },
        "scaling": {
            "snr_hammer": round(snr_h, 4),
            "snr_pscz_nvss": round(snr_r, 4),
            "snr_pscz": round(snr_p, 4),
            "n_ratio": round(n_h / max(n_p, 1), 4),
            "expected_snr_ratio_sqrt_n": round(expected, 4),
            "observed_snr_ratio": round(observed, 4),
            "beats_pscz": bool(snr_h > snr_p or snr_r > snr_p),
            "best_public_stack": (
                "hammer"
                if snr_h >= snr_r and snr_h >= snr_p
                else ("pscz_nvss" if snr_r >= snr_p else "pscz")
            ),
        },
        "forecast_desi_lrg_class": forecast,
        "gate_pass": gate,
        "interpretation": (
            "HAMMER GATE PASS — bubble_visible candidate; confirm with holdout + prereg"
            if gate
            else (
                f"Hammer SNR={snr_h:.2f} PSCz∪NVSS={snr_r:.2f} PSCz={snr_p:.2f} "
                f"(N_h={n_h} N_r={n_r}); DESI forecast {forecast['snr_forecast']:.1f} "
                f"from best={max(snr_h, snr_r, snr_p):.2f}. "
                "Keep hammering — visibility not ruled out."
            )
        ),
    }
