"""Human-readable and JSON serialization for DetectionReport."""

from __future__ import annotations

import json
from pathlib import Path

from polomni.observatory.scoring.rble_signature import DetectionReport


def format_report(report: DetectionReport) -> str:
    """Format a :class:`DetectionReport` as a Rich-friendly text summary."""
    flags = report.falsification_flags
    flag_lines = "\n".join(f"  - {k}: {'PASS' if v else 'FAIL'}" for k, v in flags.items())
    axis = report.preferred_axis
    return (
        f"RBLE Detection Report\n"
        f"{'=' * 40}\n"
        f"Score S_RBLE     : {report.rble_score:.4f}\n"
        f"Null significance: {report.null_sigma:.2f} σ\n"
        f"Preferred axis   : [{axis[0]:.4f}, {axis[1]:.4f}, {axis[2]:.4f}]\n"
        f"Timestamp (UTC)  : {report.timestamp.isoformat()}\n"
        f"Falsification flags:\n{flag_lines}\n"
    )


def save_json(report: DetectionReport, path: str | Path) -> Path:
    """Serialize *report* to JSON at *path*.

    Returns the resolved output path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = report.model_dump(mode="json")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path.resolve()
