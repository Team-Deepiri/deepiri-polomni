"""Real-sky physics bridge: align simulation closed loop to cached CMB maps."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from polomni.core.geometry import axis_separation_deg
from polomni.core.superspace.district_graph import ChoicePolicy, DistrictGraph
from polomni.integration.closed_loop import run_closed_loop_step
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.scoring.hierarchical_search import hierarchical_sky_search
from polomni.viz.cosmos.helpers import axis_lonlat, load_real_sky_map


@dataclass
class PreferredAxisMeasurement:
    """Frozen preferred axis from hierarchical search on a *real* cached map.

    This is the observational reference every neural/open-loop arm is measured
    against. Synthetic axes must never substitute for it in M2.
    """

    map_product_id: str
    nside: int
    axis: list[float]
    rble_score: float
    lon_deg: float
    lat_deg: float
    source_path: str | None
    method: str = "hierarchical_sky_search"
    neural_prescreen: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "map_product_id": self.map_product_id,
            "nside": self.nside,
            "axis": self.axis,
            "rble_score": self.rble_score,
            "lon_deg": self.lon_deg,
            "lat_deg": self.lat_deg,
            "source_path": self.source_path,
            "method": self.method,
            "neural_prescreen": self.neural_prescreen,
            "metadata": self.metadata,
            "provenance": "real_cached_cmb",
        }


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
    preferred_axis: PreferredAxisMeasurement | None = None

    def to_dict(self) -> dict[str, Any]:
        last = self.steps[-1] if self.steps else None
        return {
            "map_product_id": self.map_product_id,
            "nside": self.nside,
            "real_axis": self.real_axis,
            "real_score": self.real_score,
            "preferred_axis": self.preferred_axis.to_dict() if self.preferred_axis else None,
            "steps": [s.to_dict() for s in self.steps],
            "final_separation_deg": last.separation_deg if last else None,
            "final_alignment_quality": last.alignment_quality if last else None,
        }


def measure_preferred_axis(
    cache: DataCache,
    map_product_id: str,
    nside: int,
    *,
    full_tomogram: bool = False,
    neural_prescreen: bool = False,
    seed: int = 0,
) -> PreferredAxisMeasurement:
    """Measure the preferred axis on a cached WMAP/Planck product (not synthetic)."""
    cmb, product_id, path = load_real_sky_map(
        map_product_id=map_product_id,
        nside=nside,
        cache=cache,
    )
    if path is None:
        raise FileNotFoundError(
            f"No cached real map for {map_product_id} — run: poetry run polomni data fetch"
        )
    detection = hierarchical_sky_search(
        cmb,
        coarse_nside=min(16, nside // 4 or 16),
        seed=seed,
        full_tomogram=full_tomogram,
        report_n_eta=48,
        neural_prescreen=neural_prescreen,
    )
    axis = np.asarray(detection.preferred_axis, dtype=float)
    axis = axis / (np.linalg.norm(axis) + 1e-15)
    lon, lat = axis_lonlat(axis)
    meta = dict(detection.metadata or {})
    meta["falsification_flags"] = detection.falsification_flags
    return PreferredAxisMeasurement(
        map_product_id=product_id,
        nside=nside,
        axis=axis.tolist(),
        rble_score=float(detection.rble_score),
        lon_deg=lon,
        lat_deg=lat,
        source_path=str(path),
        neural_prescreen=neural_prescreen,
        metadata=meta,
    )


def scan_real_sky_axis(
    cache: DataCache,
    map_product_id: str,
    nside: int,
    *,
    full_tomogram: bool = False,
    neural_prescreen: bool = False,
) -> tuple[np.ndarray, float]:
    """Load cached WMAP/Planck map and run hierarchical RBLE sky search."""
    m = measure_preferred_axis(
        cache,
        map_product_id,
        nside,
        full_tomogram=full_tomogram,
        neural_prescreen=neural_prescreen,
    )
    return np.asarray(m.axis, dtype=float), float(m.rble_score)


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
    policy: ChoicePolicy = ChoicePolicy.AXIS_BIASED,
    checkpoint_dir: str | Path | None = None,
    neural_prescreen_real: bool = False,
) -> PhysicsLoopResult:
    """Closed loop where each step biases simulation toward the real-sky preferred axis.

    When ``policy`` is ``NEURAL``, Graph-NODE checkpoints propose branch weights /
    bias blending with the real-sky axis each step.
    """
    from polomni.neural.guidance import NeuralGuidance

    cache = cache or DataCache()
    preferred = measure_preferred_axis(
        cache,
        map_product_id,
        nside,
        neural_prescreen=neural_prescreen_real,
        seed=seed,
    )
    real_axis = np.asarray(preferred.axis, dtype=float)
    real_list = preferred.axis
    real_score = preferred.rble_score

    guidance = (
        NeuralGuidance(checkpoint_dir=checkpoint_dir)
        if policy == ChoicePolicy.NEURAL
        else None
    )

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
        bias_axis: list[float] | np.ndarray = real_list
        branch_weights = None
        step_policy = policy
        lr = feedback_learning_rate

        if guidance is not None:
            proposal = guidance.propose(
                graph,
                active_parent,
                num_choices=num_choices,
                last_recovered_axis=real_list,
            )
            step_policy = proposal["policy"]
            neural_bias = np.asarray(proposal["bias_axis"], dtype=float)
            neural_bias = neural_bias / (np.linalg.norm(neural_bias) + 1e-15)
            real_u = real_axis / (np.linalg.norm(real_axis) + 1e-15)
            bias_axis = 0.45 * neural_bias + 0.55 * real_u
            bias_axis = bias_axis / (np.linalg.norm(bias_axis) + 1e-15)
            branch_weights = proposal["branch_weights"]
            lr = max(feedback_learning_rate, 0.25)

        loop_result = run_closed_loop_step(
            graph,
            active_parent,
            step=step,
            num_choices=num_choices,
            nside=nside,
            seed=seed,
            policy=step_policy,
            bias_axis=bias_axis,
            branch_weights=branch_weights,
            apply_feedback=True,
            feedback_target_axis=real_axis,
            feedback_learning_rate=lr,
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
        preferred_axis=preferred,
    )
