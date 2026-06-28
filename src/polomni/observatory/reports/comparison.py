"""Load and compare RBLE detection reports."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from polomni.observatory.scoring.rble_signature import DetectionReport


def load_report(path: str | Path) -> DetectionReport:
    """Load a DetectionReport from JSON."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return DetectionReport.model_validate(data)


def list_reports(directory: str | Path = "data/reports") -> list[Path]:
    """List JSON detection reports sorted by mtime (newest first)."""
    root = Path(directory)
    if not root.is_dir():
        return []
    files = sorted(root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def latest_report(directory: str | Path = "data/reports") -> Path | None:
    reports = list_reports(directory)
    return reports[0] if reports else None


def axis_separation_deg(a: list[float] | np.ndarray, b: list[float] | np.ndarray) -> float:
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    a_arr = a_arr / (np.linalg.norm(a_arr) + 1e-15)
    b_arr = b_arr / (np.linalg.norm(b_arr) + 1e-15)
    dot = float(np.clip(np.dot(a_arr, b_arr), -1.0, 1.0))
    return float(np.degrees(np.arccos(abs(dot))))


def compare_reports(a: DetectionReport, b: DetectionReport) -> dict:
    """Compare two detection reports."""
    return {
        "score_a": a.rble_score,
        "score_b": b.rble_score,
        "score_delta": b.rble_score - a.rble_score,
        "null_sigma_a": a.null_sigma,
        "null_sigma_b": b.null_sigma,
        "axis_separation_deg": axis_separation_deg(a.preferred_axis, b.preferred_axis),
        "timestamp_a": a.timestamp.isoformat(),
        "timestamp_b": b.timestamp.isoformat(),
        "flags_a": a.falsification_flags,
        "flags_b": b.falsification_flags,
    }


def format_comparison(cmp: dict) -> str:
    return (
        "RBLE Report Comparison\n"
        f"{'=' * 40}\n"
        f"Score A          : {cmp['score_a']:.4f}\n"
        f"Score B          : {cmp['score_b']:.4f}\n"
        f"Δ Score          : {cmp['score_delta']:+.4f}\n"
        f"Null σ A / B     : {cmp['null_sigma_a']:.2f} / {cmp['null_sigma_b']:.2f}\n"
        f"Axis separation  : {cmp['axis_separation_deg']:.2f}°\n"
        f"Timestamp A      : {cmp['timestamp_a']}\n"
        f"Timestamp B      : {cmp['timestamp_b']}\n"
    )
