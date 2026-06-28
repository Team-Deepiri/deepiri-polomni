"""Regression baselines and tolerance tables for strict RBLE proofs."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_BASELINES_ROOT = Path(__file__).resolve().parents[4] / "data" / "proofs" / "baselines"


@dataclass(frozen=True)
class BaselineCheck:
    """Outcome of comparing a metric to a stored baseline."""

    proof_id: str
    metric: str
    value: float
    expected: float | None
    min_value: float | None
    max_value: float | None
    rtol: float
    atol: float
    passed: bool
    residual: float
    message: str


def baselines_root() -> Path:
    return _BASELINES_ROOT


def _load_json(name: str) -> dict[str, Any]:
    path = _BASELINES_ROOT / name
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_tolerance_table() -> dict[str, dict[str, float]]:
    """Per-proof residual tolerances (``rtol``, ``atol``)."""
    data = _load_json("tolerances.json")
    return data.get("proofs", {})


def load_real_data_baselines() -> dict[str, Any]:
    return _load_json("real_data.json")


def load_convergence_baselines() -> dict[str, Any]:
    return _load_json("convergence.json")


def tolerance_for(proof_id: str) -> tuple[float, float]:
    table = load_tolerance_table()
    entry = table.get(proof_id, {})
    return float(entry.get("rtol", 1e-6)), float(entry.get("atol", 1e-9))


def check_metric(
    proof_id: str,
    metric: str,
    value: float,
    *,
    section: str = "metrics",
) -> BaselineCheck:
    """Compare *value* against golden min/max or expected ± rtol."""
    baselines = _load_json("real_data.json") if section == "real_data" else _load_json("tolerances.json")
    block = baselines.get(proof_id, baselines.get("proofs", {}).get(proof_id, {}))
    metrics = block.get("metrics", block) if isinstance(block, dict) else {}
    spec = metrics.get(metric, {}) if isinstance(metrics, dict) else {}

    expected = spec.get("expected")
    min_value = spec.get("min")
    max_value = spec.get("max")
    rtol = float(spec.get("rtol", block.get("rtol", 1e-3)))
    atol = float(spec.get("atol", block.get("atol", 1e-6)))

    passed = True
    residual = 0.0
    parts: list[str] = []

    if expected is not None:
        expected_f = float(expected)
        residual = abs(value - expected_f)
        rel_ok = residual <= atol + rtol * abs(expected_f)
        passed = passed and rel_ok
        parts.append(f"{metric}={value:.6g} vs expected={expected_f:.6g} (Δ={residual:.3e})")

    if min_value is not None:
        min_f = float(min_value)
        if value < min_f:
            passed = False
            residual = max(residual, min_f - value)
        parts.append(f"min={min_f:.6g}")

    if max_value is not None:
        max_f = float(max_value)
        if value > max_f:
            passed = False
            residual = max(residual, value - max_f)
        parts.append(f"max={max_f:.6g}")

    if expected is None and min_value is None and max_value is None:
        rtol_def, atol_def = tolerance_for(proof_id)
        passed = math.isfinite(value)
        residual = 0.0 if passed else float("inf")
        rtol, atol = rtol_def, atol_def
        parts.append(f"{metric}={value:.6g} (finite check only)")

    return BaselineCheck(
        proof_id=proof_id,
        metric=metric,
        value=float(value),
        expected=float(expected) if expected is not None else None,
        min_value=float(min_value) if min_value is not None else None,
        max_value=float(max_value) if max_value is not None else None,
        rtol=rtol,
        atol=atol,
        passed=passed,
        residual=float(residual),
        message="; ".join(parts),
    )


def check_within(
    proof_id: str,
    metrics: dict[str, float],
    *,
    section: str = "metrics",
) -> tuple[bool, float, str]:
    """Return (all_passed, max_residual, combined_message)."""
    checks = [check_metric(proof_id, k, v, section=section) for k, v in metrics.items()]
    if not checks:
        return True, 0.0, "no metrics"
    passed = all(c.passed for c in checks)
    residual = max(c.residual for c in checks)
    msg = " | ".join(c.message for c in checks)
    return passed, residual, msg
