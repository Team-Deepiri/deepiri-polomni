"""Real-sky cosmos visualization payloads for the live lab."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np

from polomni.math.proofs.base import load_cached_suite
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.processor import calibrate_from_power_spectrum
from polomni.observatory.scoring.null_models import run_null_tier_comparison
from polomni.observatory.studies.gates import load_latest_result, run_p1_gates
from polomni.viz.cosmos.analytics import (
    axis_radial_profile,
    dual_map_comparison,
    null_score_histogram,
    sky_payload_cached,
)
from polomni.viz.cosmos.helpers import load_real_sky_map

_gate_cache: dict[str, Any] | None = None


def cosmos_sky_payload(
    *,
    map_product_id: str = "wmap_k_band",
    nside: int = 64,
    max_pixels: int = 8000,
    force: bool = False,
) -> dict[str, Any]:
    payload = sky_payload_cached(
        map_product_id=map_product_id,
        nside=nside,
        max_pixels=max_pixels,
        force=force,
    )
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    return payload


def cosmos_power_spectrum_payload(*, cache: DataCache | None = None) -> dict[str, Any]:
    cache = cache or DataCache()
    try:
        ell, dl = calibrate_from_power_spectrum(cache)
        path = cache.resolved_path("planck_cmb_tt_power")
        from polomni.observatory.pipeline.sources.cosmology import (
            load_camb_lcdm_cl,
            load_planck_tt_power,
        )

        obs = load_planck_tt_power(path) if path else None
        err = None
        residual = None
        camb_dl = None
        if obs is not None:
            err = (0.5 * (obs.dl_err_low + obs.dl_err_high)).tolist()
            camb_path = cache.resolved_path("camb_lcdm_cl")
            if camb_path is not None:
                theory = load_camb_lcdm_cl(camb_path)
                # Interpolate theory onto observed ell bins
                camb_dl = np.interp(obs.ell, theory.ell, theory.dl).tolist()
                residual = (obs.dl - np.interp(obs.ell, theory.ell, theory.dl)).tolist()

        return {
            "source": "planck_cmb_tt_power",
            "ell": ell.tolist(),
            "dl": dl.tolist(),
            "dl_err": err,
            "camb_theory": camb_dl,
            "residual": residual,
            "cached": path is not None,
        }
    except FileNotFoundError:
        return {"source": None, "ell": [], "dl": [], "cached": False}


def cached_gate_report(*, refresh: bool = False) -> dict[str, Any]:
    global _gate_cache
    if _gate_cache is None or refresh:
        _gate_cache = run_p1_gates(injection_trials=30).to_dict()
        _gate_cache["cached_at"] = datetime.now(timezone.utc).isoformat()
    return _gate_cache


def cosmos_study_payload() -> dict[str, Any]:
    gates = cached_gate_report()
    result = load_latest_result()
    suite = load_cached_suite()
    return {
        "gates": gates,
        "result": result,
        "proofs": suite.to_dict() if suite else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def cosmos_null_tiers_payload(
    *,
    map_product_id: str = "wmap_k_band",
    nside: int = 64,
    n_ensemble: int = 20,
) -> dict[str, Any]:
    cmb, pid, _ = load_real_sky_map(map_product_id=map_product_id, nside=nside)
    cmp = run_null_tier_comparison(cmb, n_ensemble=n_ensemble, seed=9)
    tiers = cmp.get("tiers", {})
    chart = {
        "labels": list(tiers.keys()),
        "p_values": [tiers[k]["p_value"] for k in tiers],
        "raw_sigma": [tiers[k]["raw_sigma"] for k in tiers],
        "score": cmp.get("score"),
        "te_correlation": cmp.get("te_correlation"),
    }
    return {
        "map_product_id": pid,
        "comparison": cmp,
        "chart": chart,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def cosmos_compare_payload(*, nside: int = 64) -> dict[str, Any]:
    payload = dual_map_comparison(nside=nside)
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    return payload


def cosmos_histogram_payload(
    *,
    map_product_id: str = "wmap_k_band",
    nside: int = 64,
    n_ensemble: int = 35,
) -> dict[str, Any]:
    cmb, pid, _ = load_real_sky_map(map_product_id=map_product_id, nside=nside)
    hist = null_score_histogram(cmb, n_ensemble=n_ensemble, seed=9)
    hist["map_product_id"] = pid
    hist["timestamp"] = datetime.now(timezone.utc).isoformat()
    return hist


def cosmos_axis_profile_payload(
    *,
    map_product_id: str = "wmap_k_band",
    nside: int = 64,
) -> dict[str, Any]:
    cmb, pid, _ = load_real_sky_map(map_product_id=map_product_id, nside=nside)
    sky = sky_payload_cached(map_product_id=pid, nside=nside, max_pixels=100)
    profile = axis_radial_profile(cmb, sky["preferred_axis"])
    profile["map_product_id"] = pid
    profile["rble_score"] = sky["rble_score"]
    profile["timestamp"] = datetime.now(timezone.utc).isoformat()
    return profile


def cosmos_live_snapshot() -> dict[str, Any]:
    result = load_latest_result()
    suite = load_cached_suite()
    gates = cached_gate_report()
    ps = cosmos_power_spectrum_payload()
    return {
        "kind": "cosmos_snapshot",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gates_passed": gates.get("all_passed", False),
        "gates": gates,
        "study": result,
        "proofs_passed": suite.passed_count if suite else 0,
        "proofs_total": len(suite.results) if suite else 0,
        "proofs_all_passed": suite.all_passed if suite else False,
        "power_spectrum_cached": ps.get("cached", False),
        "p1_supported": bool(result.get("p1_supported")) if result else False,
        "p1_falsified": bool(result.get("p1_falsified")) if result else False,
    }
