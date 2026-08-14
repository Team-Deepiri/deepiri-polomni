"""Closed RBLE loop: simulate → CMB imprint → scan → feedback."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from polomni.core.superspace.district_graph import ChoicePolicy, DistrictGraph
from polomni.core.geometry import (
    align_axis_to_reference,
    axis_separation_deg,
    coordinate_to_axis,
)
from polomni.integration.cmb_imprint import imprint_cmb_from_packets
from polomni.observatory.scoring.hierarchical_search import hierarchical_sky_search
from polomni.observatory.scoring.rble_signature import DetectionReport

FeedbackMode = Literal["coordinate_shift", "mutation_strength", "both"]


@dataclass
class LoopStepResult:
    """One closed-loop iteration."""

    step: int
    true_axis: list[float]
    recovered_axis: list[float]
    axis_error_deg: float
    rble_score: float
    graph_nodes: int
    graph_edges: int
    packets_spawned: int
    detection: DetectionReport
    feedback_applied: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "true_axis": self.true_axis,
            "recovered_axis": self.recovered_axis,
            "axis_error_deg": self.axis_error_deg,
            "rble_score": self.rble_score,
            "graph_nodes": self.graph_nodes,
            "graph_edges": self.graph_edges,
            "packets_spawned": self.packets_spawned,
            "feedback_applied": self.feedback_applied,
            "detection": self.detection.model_dump(mode="json"),
        }


def apply_scan_feedback(
    graph: DistrictGraph,
    detection: DetectionReport,
    *,
    parent_id: int,
    mode: FeedbackMode = "both",
    learning_rate: float = 0.15,
    target_axis: np.ndarray | list[float] | None = None,
) -> dict[str, Any]:
    """Feed RBLE scan result into the next simulation step.

    Shifts parent district coordinate toward the recovered axis (or *target_axis*
    when set, e.g. real-sky bridge) and adjusts ``gravity_mutation_strength``.

    Axes are undirected: if the scan returns the antipode of the parent
    coordinate, feedback flips it into the same hemisphere before the
    coordinate blend (otherwise the update shrinks/rotates away from the scar).
    """
    if parent_id not in graph.graph:
        raise KeyError(f"parent {parent_id} not in graph")

    if target_axis is not None:
        recovered = np.asarray(target_axis, dtype=float)
    else:
        recovered = np.asarray(detection.preferred_axis, dtype=float)
    recovered = recovered / (np.linalg.norm(recovered) + 1e-15)
    coord = np.asarray(graph.graph.nodes[parent_id]["coordinate"], dtype=float).ravel()
    if coord.size < 3:
        coord = np.pad(coord, (0, 3 - coord.size))

    current_axis = coordinate_to_axis(coord)
    recovered, flipped = align_axis_to_reference(recovered, current_axis)
    error_deg = axis_separation_deg(current_axis, recovered)
    applied: dict[str, Any] = {
        "axis_error_deg_before": error_deg,
        "mode": mode,
        "antipode_aligned": flipped,
        "feedback_axis": recovered.tolist(),
    }

    if mode in ("coordinate_shift", "both"):
        new_coord = (1.0 - learning_rate) * coord + learning_rate * recovered
        graph.graph.nodes[parent_id]["coordinate"] = new_coord
        applied["coordinate_shift"] = new_coord.tolist()

    if mode in ("mutation_strength", "both"):
        old_strength = graph.gravity_mutation_strength
        if error_deg > 10.0:
            graph.gravity_mutation_strength = min(0.25, old_strength * 1.1)
        elif error_deg < 3.0:
            graph.gravity_mutation_strength = max(0.02, old_strength * 0.95)
        applied["gravity_mutation_strength"] = graph.gravity_mutation_strength

    applied["axis_error_deg_after"] = axis_separation_deg(
        coordinate_to_axis(graph.graph.nodes[parent_id]["coordinate"]),
        recovered,
    )
    return applied


def run_closed_loop_step(
    graph: DistrictGraph,
    parent_id: int,
    *,
    step: int = 0,
    num_choices: int = 4,
    nside: int = 64,
    seed: int | None = None,
    policy: ChoicePolicy = ChoicePolicy.UNIFORM,
    bias_axis: np.ndarray | list[float] | None = None,
    apply_feedback: bool = True,
    scan_angles: int = 24,
    feedback_target_axis: np.ndarray | list[float] | None = None,
    feedback_learning_rate: float = 0.15,
) -> LoopStepResult:
    """Single loop: choice event → CMB imprint → RBLE scan → optional feedback."""
    packets = graph.trigger_choice_event(
        parent_id,
        num_choices=num_choices,
        policy=policy,
        bias_axis=bias_axis,
    )
    imprint_seed = (seed if seed is not None else 0) + step
    cmb, true_axis = imprint_cmb_from_packets(
        packets, graph, nside=nside, seed=imprint_seed
    )
    detection = hierarchical_sky_search(
        cmb,
        refine_samples=max(12, scan_angles // 2),
        seed=imprint_seed,
        search_n_eta=16,
        report_n_eta=32,
        full_tomogram=False,
    )
    recovered = np.asarray(detection.preferred_axis, dtype=float)
    error_deg = axis_separation_deg(true_axis, recovered)

    feedback: dict[str, Any] = {}
    if apply_feedback:
        feedback = apply_scan_feedback(
            graph,
            detection,
            parent_id=parent_id,
            target_axis=feedback_target_axis,
            learning_rate=feedback_learning_rate,
        )

    return LoopStepResult(
        step=step,
        true_axis=true_axis.tolist(),
        recovered_axis=recovered.tolist(),
        axis_error_deg=error_deg,
        rble_score=float(detection.rble_score),
        graph_nodes=graph.graph.number_of_nodes(),
        graph_edges=graph.graph.number_of_edges(),
        packets_spawned=len(packets),
        detection=detection,
        feedback_applied=feedback,
    )


def run_closed_loop(
    *,
    steps: int = 3,
    num_choices: int = 4,
    nside: int = 64,
    seed: int = 0,
    policy: ChoicePolicy = ChoicePolicy.UNIFORM,
    chain_depth: int = 1,
) -> tuple[DistrictGraph, list[LoopStepResult]]:
    """Multi-step closed loop with chained choice events on leaf districts."""
    graph = DistrictGraph(gravity_mutation_strength=0.06)
    root = graph.add_district(
        mass=10.0,
        law_of_gravity=[6.674e-11, 1.1e-52],
        coordinate=[0.2, 0.3, 0.9],
        lambda_vacuum=1.0e-52,
    )
    active_parent = root
    results: list[LoopStepResult] = []

    for step in range(steps):
        bias = None
        if results:
            bias = results[-1].recovered_axis

        result = run_closed_loop_step(
            graph,
            active_parent,
            step=step,
            num_choices=num_choices,
            nside=nside,
            seed=seed,
            policy=policy,
            bias_axis=bias,
            apply_feedback=True,
        )
        results.append(result)

        # Chain: next parent is the highest-conductance child from this event.
        children = [
            v for u, v in graph.graph.edges() if u == active_parent
        ]
        if children and chain_depth > 0:
            best = max(children, key=lambda c: graph.get_conductance(active_parent, c))
            active_parent = best

    return graph, results
