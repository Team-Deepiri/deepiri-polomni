"""Real-sky physics bridge: align simulation closed loop to cached CMB maps."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from polomni.core.geometry import axis_separation_deg
from polomni.core.superspace.district_graph import ChoicePolicy, DistrictGraph
from polomni.integration.closed_loop import run_closed_loop_step
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.scoring.hierarchical_search import hierarchical_sky_search
from polomni.viz.cosmos.helpers import load_real_sky_map


@dataclass
class PhysicsLoopStepResult:
    """One physics-loop iteration: synthetic scan vs real-sky axis."""

    step: int
    synthetic_axis: list[float]
    real_axis: list[float]
    separation_deg: float
    alignment_quality: float
    rble_score: float
    imprint_true_axis: list[float]
    feedback_applied: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "synthetic_axis": self.synthetic_axis,
            "real_axis": self.real_axis,
            "separation_deg": self.separation_deg,
            "alignment_quality": self.alignment_quality,
            "rble_score": self.rble_score,
            "imprint_true_axis": self.imprint_true_axis,
            "feedback_applied": self.feedback_applied,
        }


@dataclass
class PhysicsLoopResult:
    """Closed loop biased toward a cached real-sky preferred axis."""

    map_product_id: str
    nside: int
    real_axis: list[float]
    real_score: float
    steps: list[PhysicsLoopStepResult]
    graph: DistrictGraph

    def to_dict(self) -> dict[str, Any]:
        last = self.steps[-1] if self.steps else None
        return {
            "map_product_id": self.map_product_id,
            "nside": self.nside,
            "real_axis": self.real_axis,
            "real_score": self.real_score,
            "steps": [s.to_dict() for s in self.steps],
            "final_separation_deg": last.separation_deg if last else None,
            "final_alignment_quality": last.alignment_quality if last else None,
        }


def scan_real_sky_axis(
    cache: DataCache,
    map_product_id: str,
    nside: int,
    *,
    full_tomogram: bool = False,
) -> tuple[np.ndarray, float]:
    """Load cached WMAP/Planck map and run hierarchical RBLE sky search."""
    cmb, _, _ = load_real_sky_map(
        map_product_id=map_product_id,
        nside=nside,
        cache=cache,
    )
    detection = hierarchical_sky_search(
        cmb,
        coarse_nside=min(16, nside // 4 or 16),
        seed=0,
        full_tomogram=full_tomogram,
        report_n_eta=48,
    )
    axis = np.asarray(detection.preferred_axis, dtype=float)
    return axis, float(detection.rble_score)


def align_sim_to_real(
    synthetic_axis: np.ndarray | list[float],
    real_axis: np.ndarray | list[float],
) -> dict[str, float]:
    """Angular separation and alignment quality between synthetic and real axes."""
    syn = np.asarray(synthetic_axis, dtype=float)
    real = np.asarray(real_axis, dtype=float)
    syn = syn / (np.linalg.norm(syn) + 1e-15)
    real = real / (np.linalg.norm(real) + 1e-15)
    separation_deg = axis_separation_deg(syn, real)
    alignment_quality = float(abs(np.dot(syn, real)))
    return {
        "separation_deg": separation_deg,
        "alignment_quality": alignment_quality,
    }


def run_physics_loop(
    *,
    steps: int = 3,
    nside: int = 64,
    map_product_id: str = "wmap_k_band",
    cache: DataCache | None = None,
    seed: int = 0,
    num_choices: int = 4,
    chain_depth: int = 1,
    feedback_learning_rate: float = 0.35,
) -> PhysicsLoopResult:
    """Closed loop where each step biases simulation toward the real-sky preferred axis."""
    cache = cache or DataCache()
    real_axis, real_score = scan_real_sky_axis(cache, map_product_id, nside)
    real_list = real_axis.tolist()

    graph = DistrictGraph(gravity_mutation_strength=0.06)
    root = graph.add_district(
        mass=10.0,
        law_of_gravity=[6.674e-11, 1.1e-52],
        coordinate=real_list,
        lambda_vacuum=1.0e-52,
    )
    active_parent = root
    step_results: list[PhysicsLoopStepResult] = []

    for step in range(steps):
        loop_result = run_closed_loop_step(
            graph,
            active_parent,
            step=step,
            num_choices=num_choices,
            nside=nside,
            seed=seed,
            policy=ChoicePolicy.AXIS_BIASED,
            bias_axis=real_list,
            apply_feedback=True,
            feedback_target_axis=real_axis,
            feedback_learning_rate=feedback_learning_rate,
        )
        alignment = align_sim_to_real(loop_result.recovered_axis, real_axis)
        step_results.append(
            PhysicsLoopStepResult(
                step=step,
                synthetic_axis=loop_result.recovered_axis,
                real_axis=real_list,
                separation_deg=alignment["separation_deg"],
                alignment_quality=alignment["alignment_quality"],
                rble_score=loop_result.rble_score,
                imprint_true_axis=loop_result.true_axis,
                feedback_applied=loop_result.feedback_applied,
            )
        )

        children = [v for u, v in graph.graph.edges() if u == active_parent]
        if children and chain_depth > 0:
            best = max(children, key=lambda c: graph.get_conductance(active_parent, c))
            active_parent = best

    return PhysicsLoopResult(
        map_product_id=map_product_id,
        nside=nside,
        real_axis=real_list,
        real_score=real_score,
        steps=step_results,
        graph=graph,
    )
