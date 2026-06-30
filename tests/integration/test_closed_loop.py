"""Integration tests for closed RBLE simulation loop."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.core.superspace.district_graph import ChoicePolicy, DistrictGraph
from polomni.integration.closed_loop import run_closed_loop, run_closed_loop_step
from polomni.core.geometry import axis_separation_deg
from polomni.integration.cmb_imprint import imprint_cmb_from_packets
from polomni.integration.workflow import run_lab_workflow
from polomni.observatory.scoring.hierarchical_search import hierarchical_sky_search
from polomni.observatory.scoring.rble_signature import compute_rble_signature


@pytest.mark.integration
def test_imprint_and_recover_axis() -> None:
    """District sim imprints CMB; RBLE scan recovers axis within tolerance."""
    graph = DistrictGraph()
    root = graph.add_district(
        mass=5.0,
        law_of_gravity=[1.0, 1e-52],
        coordinate=[0.1, 0.2, 0.97],
        lambda_vacuum=1e-52,
    )
    packets = graph.trigger_choice_event(root, 4, policy=ChoicePolicy.AXIS_BIASED)
    cmb, true_axis = imprint_cmb_from_packets(
        packets, graph, nside=32, seed=1, base_amplitude=12.0
    )
    detection = hierarchical_sky_search(
        cmb,
        coarse_nside=16,
        refine_samples=16,
        coarse_scan_angles=12,
        seed=1,
    )
    recovered = np.asarray(detection.preferred_axis)
    dot = float(np.clip(abs(np.dot(
        true_axis / (np.linalg.norm(true_axis) + 1e-15),
        recovered / (np.linalg.norm(recovered) + 1e-15),
    )), -1.0, 1.0))
    error = float(np.degrees(np.arccos(dot)))
    assert detection.rble_score > 0.1
    assert error < 15.0


@pytest.mark.integration
def test_closed_loop_improves_or_stable() -> None:
    """Multi-step loop runs and final axis error is bounded."""
    _, results = run_closed_loop(steps=3, num_choices=4, nside=32, seed=2)
    assert len(results) == 3
    errors = [r.axis_error_deg for r in results]
    assert all(e < 90.0 for e in errors)
    assert results[-1].rble_score > 0.05
    assert results[-1].rble_score > 0.0


@pytest.mark.integration
def test_feedback_shifts_coordinate() -> None:
    graph = DistrictGraph()
    root = graph.add_district(
        mass=1.0,
        law_of_gravity=[1.0, 1e-52],
        coordinate=[1.0, 0.0, 0.0],
        lambda_vacuum=1e-52,
    )
    before = np.array(graph.graph.nodes[root]["coordinate"], dtype=float).copy()
    run_closed_loop_step(graph, root, step=0, nside=32, seed=0, apply_feedback=True)
    after = np.array(graph.graph.nodes[root]["coordinate"], dtype=float)
    assert not np.allclose(before, after)


@pytest.mark.integration
def test_lab_workflow_closed_loop_default() -> None:
    result = run_lab_workflow(
        target_nside=32,
        closed_loop_steps=2,
        simulation_choices=3,
        use_real_data_pipeline=False,
    )
    assert result.pipeline_result is None
    assert len(result.closed_loop) == 2
    assert "inflation" in result.subsystems
    assert "neural" in result.subsystems
    assert "uqe_bridge" in result.subsystems
    payload = result.to_dict()
    assert "closed_loop" in payload
    assert payload["simulation_summary"]["mode"] == "closed_loop"
