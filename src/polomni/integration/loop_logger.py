"""Persist closed-loop telemetry for neural corpus and physics analysis."""

from __future__ import annotations

import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from polomni.core.superspace.district_graph import ChoicePolicy, DistrictGraph
from polomni.integration.closed_loop import LoopStepResult, run_closed_loop


def _git_sha() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def log_loop_run(
    graph: DistrictGraph,
    steps: list[LoopStepResult],
    *,
    policy: ChoicePolicy,
    nside: int,
    seed: int,
    output_dir: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Write one closed-loop run to ``data/loop_runs/{run_id}.json``."""
    output_dir = output_dir or Path("data/loop_runs")
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:12]
    payload: dict[str, Any] = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "policy": policy.value,
        "nside": nside,
        "seed": seed,
        "steps": [s.to_dict() for s in steps],
        "graph_snapshot": graph.to_dict(),
        "summary": {
            "n_steps": len(steps),
            "final_axis_error_deg": steps[-1].axis_error_deg if steps else None,
            "mean_rble_score": float(sum(s.rble_score for s in steps) / max(len(steps), 1)),
            "graph_nodes": graph.graph.number_of_nodes(),
            "graph_edges": graph.graph.number_of_edges(),
        },
    }
    if extra:
        payload["extra"] = extra
    path = output_dir / f"{run_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def run_and_log_loop(
    *,
    steps: int = 3,
    num_choices: int = 4,
    nside: int = 32,
    seed: int = 0,
    policy: ChoicePolicy = ChoicePolicy.AXIS_BIASED,
    output_dir: Path | None = None,
) -> tuple[DistrictGraph, list[LoopStepResult], Path]:
    """Run closed loop and persist telemetry."""
    graph, results = run_closed_loop(
        steps=steps,
        num_choices=num_choices,
        nside=nside,
        seed=seed,
        policy=policy,
    )
    path = log_loop_run(
        graph,
        results,
        policy=policy,
        nside=nside,
        seed=seed,
        output_dir=output_dir,
    )
    return graph, results, path
