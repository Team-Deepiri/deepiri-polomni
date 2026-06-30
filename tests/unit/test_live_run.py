"""Unit tests for real-data live pipeline helpers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from polomni.core.superspace.district_graph import DistrictGraph
from polomni.integration.live_run import log_physics_loop_run
from polomni.integration.real_sky_bridge import PhysicsLoopResult, PhysicsLoopStepResult


def test_log_physics_loop_run_writes_convergence(tmp_path: Path) -> None:
    steps = [
        PhysicsLoopStepResult(
            step=0,
            synthetic_axis=[0.1, 0.2, 0.97],
            real_axis=[0.0, 0.0, 1.0],
            separation_deg=12.0,
            alignment_quality=0.9,
            rble_score=1.1,
            imprint_true_axis=[0.0, 0.0, 1.0],
        ),
        PhysicsLoopStepResult(
            step=1,
            synthetic_axis=[0.05, 0.1, 0.99],
            real_axis=[0.0, 0.0, 1.0],
            separation_deg=4.0,
            alignment_quality=0.98,
            rble_score=1.2,
            imprint_true_axis=[0.0, 0.0, 1.0],
        ),
    ]
    result = PhysicsLoopResult(
        map_product_id="wmap_k_band",
        nside=32,
        real_axis=[0.0, 0.0, 1.0],
        real_score=1.05,
        steps=steps,
        graph=DistrictGraph(),
    )
    path = log_physics_loop_run(result, output_dir=tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["kind"] == "physics_loop"
    assert payload["convergence_improving"] is True
    assert payload["final_separation_deg"] == 4.0
