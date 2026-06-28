"""P1 pre-registered blind study runner."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from polomni.observatory.filters.radon_bifurcation import inverse_radon_bifurcation_filter
from polomni.observatory.filters.string_filter import string_landscape_filter
from polomni.observatory.ingest.healpix_loader import downsample_map, load_healpix_map
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.scoring.hierarchical_search import hierarchical_sky_search
from polomni.observatory.scoring.multiple_testing import (
    count_sky_search_tests,
    passes_bonferroni,
)
from polomni.observatory.scoring.null_models import NullTier, run_null_tier_comparison, te_correlation_along_axis
from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
from polomni.observatory.studies.config import P1StudyConfig, load_p1_config

_RESULT_PATH = Path("data/studies/p1_holdout/RESULT.json")


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _apply_filters(cmb_map: np.ndarray, config: P1StudyConfig) -> np.ndarray:
    filt = config.filters
    sf = filt.get("string_filter", {})
    mapped = string_landscape_filter(cmb_map, sf if isinstance(sf, dict) else {})
    angles = filt.get("radon_bifurcation_angles", [])
    if angles:
        return inverse_radon_bifurcation_filter(mapped, np.asarray(angles, dtype=float))
    return mapped


def run_p1_study(
    config_path: Path | None = None,
    *,
    cache: DataCache | None = None,
    blind: bool = False,
    calibration: bool = False,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Execute P1 study per frozen config; write RESULT.json."""
    config = load_p1_config(config_path)
    cache = cache or DataCache()
    maps = config.maps

    if blind:
        product_id = str(maps.get("holdout_product_id", "planck_smica_cmb"))
        mode = "holdout_blind"
    elif calibration:
        product_id = str(maps.get("calibration_product_id", "wmap_k_band"))
        mode = "calibration"
    else:
        product_id = str(maps.get("calibration_product_id", "wmap_k_band"))
        mode = "exploratory"

    path = cache.resolved_path(product_id)
    if path is None:
        msg = f"Missing cached map {product_id!r}; fetch before running study"
        raise FileNotFoundError(msg)

    nside = int(config.resolution.get("search_nside", 128))
    raw = load_healpix_map(path, field="T")
    cmb = downsample_map(raw, nside)
    filtered = _apply_filters(cmb, config)

    search = config.search
    detection = hierarchical_sky_search(
        filtered,
        coarse_nside=int(search.get("coarse_nside", 16)),
        refine_cone_deg=float(search.get("refine_cone_deg", 15.0)),
        refine_samples=int(search.get("refine_samples", 24)),
        coarse_scan_angles=int(search.get("coarse_scan_angles", 12)),
        seed=int(search.get("seed", 0)),
    )

    tier_names = [NullTier(t) for t in config.null_tiers]
    null_cmp = run_null_tier_comparison(
        filtered,
        tier_names,
        n_ensemble=config.null_ensemble_size,
        seed=11,
        n_hat=detection.preferred_axis,
    )

    n_tests = count_sky_search_tests(
        scan_angles=int(search.get("coarse_scan_angles", 12)),
        hierarchical_refine_samples=int(search.get("refine_samples", 24)),
    )
    null_maps = generate_null_ensemble(config.null_ensemble_size, nside, seed=7)
    null_scores = [
        hierarchical_sky_search(m, coarse_nside=min(16, nside // 4 or 16)).rble_score
        for m in null_maps
    ]
    mu = float(np.mean(null_scores))
    sigma = float(np.std(null_scores))
    raw_sigma = (detection.rble_score - mu) / (sigma + 1e-12)
    bonf_pass, bonf_sigma, bonf_alpha = passes_bonferroni(raw_sigma, n_tests)

    te_rho = te_correlation_along_axis(filtered, detection.preferred_axis)
    te_null = [
        te_correlation_along_axis(m, detection.preferred_axis) for m in null_maps[: min(10, len(null_maps))]
    ]
    te_mu = float(np.mean(te_null))
    te_sig = float(np.std(te_null))
    te_sigma = (te_rho - te_mu) / (te_sig + 1e-12)
    te_threshold = float(config.significance.get("te_sigma_threshold", 3.0))
    te_pass = te_sigma >= te_threshold

    alpha = float(config.significance.get("alpha", 0.01))
    tier_pass = all(
        tier["p_value"] * n_tests <= alpha for tier in null_cmp["tiers"].values()
    )
    p1_supported = bonf_pass and tier_pass and te_pass

    result: dict[str, Any] = {
        "study_id": config.study_id,
        "config_version": config.version,
        "registered_before_holdout": config.registered_before_holdout,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "mode": mode,
        "blind": blind,
        "map_product_id": product_id,
        "nside": nside,
        "detection": detection.model_dump(mode="json"),
        "null_tier_comparison": null_cmp,
        "ensemble_null": {"mu": mu, "sigma": sigma, "raw_sigma": raw_sigma},
        "bonferroni": {
            "n_tests": n_tests,
            "corrected_sigma": bonf_sigma,
            "alpha": bonf_alpha,
            "pass": bonf_pass,
        },
        "te_correlation": {
            "rho": te_rho,
            "null_mu": te_mu,
            "null_sigma": te_sig,
            "sigma": te_sigma,
            "pass": te_pass,
        },
        "p1_supported": p1_supported,
        "p1_falsified": not p1_supported and blind,
    }

    out = output_path or _RESULT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["result_path"] = str(out.resolve())
    return result
