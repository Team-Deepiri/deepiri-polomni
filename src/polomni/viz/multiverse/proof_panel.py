"""Multiverse proof visualization payload for frontend."""

from __future__ import annotations

from typing import Any

import numpy as np

from polomni.core.superspace.district_graph import ChoicePolicy, DistrictGraph
from polomni.integration.closed_loop import run_closed_loop
from polomni.integration.multiverse_proof import run_multiverse_proof
from polomni.viz.multiverse.serializers import _graph_to_viz_payload


def multiverse_proof_panel(*, quick: bool = True) -> dict[str, Any]:
    """API payload: proof metrics + live multiverse graph + convergence series."""
    report = run_multiverse_proof(quick=quick)

    graph, results = run_closed_loop(
        steps=3 if not quick else 2,
        num_choices=5,
        nside=32,
        seed=11,
        policy=ChoicePolicy.AXIS_BIASED,
    )

    loop_series = {
        "step": [r.step for r in results],
        "axis_error_deg": [r.axis_error_deg for r in results],
        "rble_score": [r.rble_score for r in results],
        "true_axis": [r.true_axis for r in results],
        "recovered_axis": [r.recovered_axis for r in results],
    }

    # Longer multiverse chain for 3D viz
    big_graph = DistrictGraph()
    root = big_graph.add_district(
        mass=10.0,
        law_of_gravity=[6.674e-11, 1.1e-52],
        coordinate=[0.2, 0.3, 0.9],
        lambda_vacuum=1.0e-52,
    )
    parent = root
    branch_depth: list[int] = []
    for depth in range(4):
        packets = big_graph.trigger_choice_event(parent, 4, policy=ChoicePolicy.AXIS_BIASED)
        branch_depth.append(len(packets))
        children = [v for u, v in big_graph.graph.edges() if u == parent]
        if not children:
            break
        parent = max(children, key=lambda c: big_graph.get_conductance(parent, c))

    conductance_matrix = []
    for u, v, d in big_graph.graph.edges(data=True):
        conductance_matrix.append(
            {"source": int(u), "target": int(v), "g": float(d.get("conductance", 0.0))}
        )

    return {
        "proof": report.to_dict(),
        "loop_series": loop_series,
        "graph": _graph_to_viz_payload(graph),
        "multiverse_graph": _graph_to_viz_payload(big_graph),
        "branch_depth": branch_depth,
        "conductance_matrix": conductance_matrix,
        "evidence_tier": _evidence_tier(report.pass_rate, report.all_passed),
    }


def _evidence_tier(pass_rate: float, all_passed: bool) -> str:
    if all_passed:
        return "computational_proof_complete"
    if pass_rate >= 0.85:
        return "strong_computational_evidence"
    if pass_rate >= 0.6:
        return "partial_evidence"
    return "insufficient"
