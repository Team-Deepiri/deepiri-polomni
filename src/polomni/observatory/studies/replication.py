"""Gate 5 independent replication verification against golden holdout reference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.studies.p1_runner import run_p1_study
from polomni.observatory.studies.results import (
    CANONICAL_BLIND_RESULT,
    InvalidResultPathError,
    REPLICATION_RESULT,
    is_canonical_blind_path,
    load_canonical_blind_result,
)

_GOLDEN_PATH = Path("data/studies/p1_holdout/golden_holdout_v1.json")
_REPLICATION_REPORT = Path("data/studies/p1_holdout/replication/VERIFY.json")


def load_golden_reference(path: Path | None = None) -> dict[str, Any]:
    p = path or _GOLDEN_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def verify_cache_checksums(
    golden: dict[str, Any] | None = None,
    *,
    cache: DataCache | None = None,
) -> tuple[bool, list[str]]:
    """Ensure cached mission FITS match golden SHA256 pins."""
    golden = golden or load_golden_reference()
    required: dict[str, str] = golden.get("required_cache_sha256", {})
    cache = cache or DataCache()
    manifest_path = cache.root / "manifest.json"
    if not manifest_path.is_file():
        return False, ["cache manifest missing — run: polomni data fetch --wmap --planck"]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("entries", {})
    errors: list[str] = []
    for product_id, expected_sha in required.items():
        entry = entries.get(product_id)
        if entry is None:
            errors.append(f"missing cache product: {product_id}")
            continue
        actual = entry.get("content_sha256")
        if actual is None:
            errors.append(f"no checksum recorded for {product_id}")
        elif actual != expected_sha:
            errors.append(f"{product_id} sha256 mismatch (expected {expected_sha[:12]}…)")
    return len(errors) == 0, errors


def _axis_agreement(a: list[float], b: list[float]) -> float:
    va = np.asarray(a, dtype=float)
    vb = np.asarray(b, dtype=float)
    va /= np.linalg.norm(va) + 1e-15
    vb /= np.linalg.norm(vb) + 1e-15
    return float(abs(np.dot(va, vb)))


def compare_holdout_to_golden(
    result: dict[str, Any],
    golden: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """Compare holdout RESULT.json fields to golden reference within tolerances."""
    golden = golden or load_golden_reference()
    exp = golden["expected_holdout"]
    tol = golden.get("tolerances", {})
    score_tol = float(tol.get("rble_score_abs", 0.05))
    axis_min = float(tol.get("axis_dot_min", 0.995))
    p_rel = float(tol.get("tier_p_value_rel", 0.15))

    errors: list[str] = []
    if result.get("map_product_id") != exp["map_product_id"]:
        errors.append(f"map_product_id {result.get('map_product_id')!r} != {exp['map_product_id']!r}")
    if int(result.get("nside", 0)) != int(exp["nside"]):
        errors.append(f"nside {result.get('nside')} != {exp['nside']}")
    if bool(result.get("blind")) != bool(exp["blind"]):
        errors.append("blind flag mismatch")

    score = float(result["detection"]["rble_score"])
    if abs(score - float(exp["rble_score"])) > score_tol:
        errors.append(f"rble_score {score:.6f} outside ±{score_tol} of {exp['rble_score']}")

    axis = result["detection"]["preferred_axis"]
    dot = _axis_agreement(axis, exp["preferred_axis"])
    if dot < axis_min:
        errors.append(f"preferred_axis agreement {dot:.4f} < {axis_min}")

    if bool(result.get("p1_supported")) != bool(exp["p1_supported"]):
        errors.append(f"p1_supported {result.get('p1_supported')} != {exp['p1_supported']}")
    if bool(result.get("p1_falsified")) != bool(exp["p1_falsified"]):
        errors.append(f"p1_falsified {result.get('p1_falsified')} != {exp['p1_falsified']}")

    tiers = result.get("null_tier_comparison", {}).get("tiers", {})
    for tier, expected_p in exp.get("null_tier_p_values", {}).items():
        actual_p = tiers.get(tier, {}).get("p_value")
        if actual_p is None:
            errors.append(f"missing null tier {tier}")
            continue
        if expected_p == 0:
            if actual_p > 1e-50:
                errors.append(f"{tier} p_value expected ~0, got {actual_p}")
        elif abs(actual_p - expected_p) / expected_p > p_rel:
            errors.append(f"{tier} p_value {actual_p:.4g} outside rel tol of {expected_p:.4g}")

    return len(errors) == 0, errors


def run_independent_replication(
    *,
    rerun: bool = False,
    golden_path: Path | None = None,
    output_path: Path | None = None,
    cache: DataCache | None = None,
) -> dict[str, Any]:
    """Gate 5: verify cache pins and holdout metrics match golden reference."""
    replication_path = output_path or REPLICATION_RESULT
    if is_canonical_blind_path(replication_path):
        raise InvalidResultPathError("Replication reruns cannot target the canonical blind result")

    golden = load_golden_reference(golden_path)
    cache = cache or DataCache()
    cache_ok, cache_errors = verify_cache_checksums(golden, cache=cache)

    if rerun:
        result = run_p1_study(
            blind=True,
            cache=cache,
            output_path=replication_path,
            artifact_role="replication_rerun",
        )
        rerun_performed = True
        source_result_path = result["result_path"]
    else:
        loaded = load_canonical_blind_result()
        if loaded is None:
            result = run_p1_study(
                blind=True,
                cache=cache,
                output_path=replication_path,
                artifact_role="replication_rerun",
            )
            rerun_performed = True
            source_result_path = result["result_path"]
        else:
            result = loaded
            rerun_performed = False
            source_result_path = str(CANONICAL_BLIND_RESULT.resolve())
    result_ok, result_errors = compare_holdout_to_golden(result, golden)
    passed = cache_ok and result_ok

    report: dict[str, Any] = {
        "gate": "G5",
        "version": golden.get("version"),
        "rerun": rerun_performed,
        "source_result_path": source_result_path,
        "passed": passed,
        "cache_checksums_ok": cache_ok,
        "holdout_match_ok": result_ok,
        "cache_errors": cache_errors,
        "holdout_errors": result_errors,
        "observed": {
            "rble_score": result["detection"]["rble_score"],
            "preferred_axis": result["detection"]["preferred_axis"],
            "p1_supported": result.get("p1_supported"),
            "p1_falsified": result.get("p1_falsified"),
        },
        "golden_rble_score": golden["expected_holdout"]["rble_score"],
    }

    out = _REPLICATION_REPORT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["report_path"] = str(out.resolve())
    return report
