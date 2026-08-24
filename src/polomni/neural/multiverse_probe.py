"""Neural multiverse probe — use Graph-NODE / scar models against real sky.

Honest scope
------------
This does **not** declare the multiverse proven. It tests whether neural models
trained on closed-loop district dynamics produce **sharper alignment** between
simulated scars and preferred axes on public CMB maps than non-neural baselines.

If neural guidance systematically pulls simulation toward the same sky axis that
independent hierarchical search finds on WMAP/Planck — under a frozen protocol —
that is *computational evidence for a controllable RBLE interaction channel*.
Observational discovery still requires a new pre-registered claim that survives
blind holdout (P1 already falsified).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from polomni.core.superspace.district_graph import ChoicePolicy
from polomni.integration.real_sky_bridge import (
    PhysicsLoopResult,
    PreferredAxisMeasurement,
    align_sim_to_real,
    measure_preferred_axis,
    run_physics_loop,
)
from polomni.neural.guidance import NeuralGuidance
from polomni.observatory.pipeline.cache import DataCache
from polomni.viz.cosmos.helpers import load_real_sky_map


@dataclass
class ArmProbe:
    name: str
    final_separation_deg: float
    mean_separation_deg: float
    final_alignment: float
    mean_alignment: float
    real_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "final_separation_deg": self.final_separation_deg,
            "mean_separation_deg": self.mean_separation_deg,
            "final_alignment": self.final_alignment,
            "mean_alignment": self.mean_alignment,
            "real_score": self.real_score,
        }


@dataclass
class MultiverseProbeReport:
    """Neural vs baseline physics-loop probe on cached real sky."""

    study_id: str = "m2_neural_real_sky_probe"
    ran_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    map_product_id: str = ""
    nside: int = 32
    steps: int = 0
    real_axis: list[float] = field(default_factory=list)
    real_score: float = 0.0
    preferred_axis: dict[str, Any] | None = None
    neural_prescreen_axis: list[float] | None = None
    neural_prescreen_sep_deg: float | None = None
    arms: dict[str, ArmProbe] = field(default_factory=dict)
    neural_beats_uniform: bool = False
    improvement_deg: float = 0.0
    claim: str = ""
    caveats: list[str] = field(default_factory=list)
    guidance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "study_id": self.study_id,
            "ran_at": self.ran_at,
            "map_product_id": self.map_product_id,
            "nside": self.nside,
            "steps": self.steps,
            "real_axis": self.real_axis,
            "real_score": self.real_score,
            "preferred_axis": self.preferred_axis,
            "neural_prescreen_axis": self.neural_prescreen_axis,
            "neural_prescreen_sep_deg": self.neural_prescreen_sep_deg,
            "arms": {k: v.to_dict() for k, v in self.arms.items()},
            "neural_beats_uniform": self.neural_beats_uniform,
            "improvement_deg": self.improvement_deg,
            "claim": self.claim,
            "caveats": self.caveats,
            "guidance": self.guidance,
        }


def _arm_from_physics(name: str, result: PhysicsLoopResult) -> ArmProbe:
    seps = [s.separation_deg for s in result.steps]
    aligns = [s.alignment_quality for s in result.steps]
    return ArmProbe(
        name=name,
        final_separation_deg=float(seps[-1]) if seps else float("nan"),
        mean_separation_deg=float(np.mean(seps)) if seps else float("nan"),
        final_alignment=float(aligns[-1]) if aligns else float("nan"),
        mean_alignment=float(np.mean(aligns)) if aligns else float("nan"),
        real_score=float(result.real_score),
    )


def run_open_loop_toward_sky(
    *,
    real_axis: np.ndarray,
    steps: int = 4,
    nside: int = 32,
    seed: int = 0,
    policy: ChoicePolicy = ChoicePolicy.UNIFORM,
    checkpoint_dir: Path | str | None = None,
    use_real_as_feedback: bool = False,
) -> ArmProbe:
    """Closed-loop from a *neutral* start — does policy alone approach real axis?"""
    from polomni.integration.closed_loop import run_closed_loop_step
    from polomni.neural.guidance import NeuralGuidance
    from polomni.core.superspace.district_graph import DistrictGraph

    guidance = NeuralGuidance(checkpoint_dir=checkpoint_dir) if policy == ChoicePolicy.NEURAL else None
    # Start away from the real axis so feedback has work to do.
    start = np.array([0.0, 0.0, 1.0], dtype=float)
    if abs(float(np.dot(start, real_axis / (np.linalg.norm(real_axis) + 1e-15)))) > 0.9:
        start = np.array([1.0, 0.0, 0.0], dtype=float)

    graph = DistrictGraph(gravity_mutation_strength=0.08)
    parent = graph.add_district(
        mass=10.0,
        law_of_gravity=[6.674e-11, 1.1e-52],
        coordinate=start.tolist(),
        lambda_vacuum=1.0e-52,
    )
    seps: list[float] = []
    aligns: list[float] = []
    scores: list[float] = []
    last_recovered = None

    for step in range(steps):
        bias = last_recovered
        weights = None
        step_policy = policy
        if guidance is not None:
            prop = guidance.propose(
                graph, parent, num_choices=4, last_recovered_axis=last_recovered
            )
            step_policy = prop["policy"]
            bias = prop["bias_axis"]
            weights = prop["branch_weights"]
            # Locksmith: imprint lives at parent coordinate — move the scar
            # site toward the neural axis *before* the choice/imprint step.
            neural_u = np.asarray(bias, dtype=float)
            neural_u = neural_u / (np.linalg.norm(neural_u) + 1e-15)
            coord = np.asarray(graph.graph.nodes[parent]["coordinate"], dtype=float)
            lr = 0.85 if last_recovered is None else 0.45
            graph.graph.nodes[parent]["coordinate"] = (1.0 - lr) * coord + lr * neural_u

        result = run_closed_loop_step(
            graph,
            parent,
            step=step,
            num_choices=4,
            nside=nside,
            seed=seed + step,
            policy=step_policy,
            bias_axis=bias,
            branch_weights=weights,
            apply_feedback=True,
            feedback_target_axis=real_axis if use_real_as_feedback else None,
            feedback_learning_rate=0.35 if use_real_as_feedback else 0.25,
        )
        last_recovered = result.recovered_axis
        al = align_sim_to_real(result.recovered_axis, real_axis)
        seps.append(al["separation_deg"])
        aligns.append(al["alignment_quality"])
        scores.append(result.rble_score)

        children = [v for u, v in graph.graph.edges() if u == parent]
        if children:
            parent = max(children, key=lambda c: graph.get_conductance(parent, c))

    return ArmProbe(
        name=f"open_{policy.value}",
        final_separation_deg=float(seps[-1]),
        mean_separation_deg=float(np.mean(seps)),
        final_alignment=float(aligns[-1]),
        mean_alignment=float(np.mean(aligns)),
        real_score=float(np.mean(scores)),
    )


def run_multiverse_probe(
    *,
    map_product_id: str = "wmap_k_band",
    nside: int = 32,
    steps: int = 4,
    seed: int = 0,
    cache: DataCache | None = None,
    checkpoint_dir: Path | str | None = None,
) -> MultiverseProbeReport:
    """Compare open-loop neural vs uniform approach to the real preferred axis.

    Primary win rule: open-loop neural final separation is ≥ **5°** better than
    open-loop uniform (models must find the sky axis without being handed it as
    a hard feedback target). Physics-loop arms remain for telemetry.
    """
    cache = cache or DataCache()
    guidance = NeuralGuidance(checkpoint_dir=checkpoint_dir)

    preferred = measure_preferred_axis(
        cache, map_product_id, nside, full_tomogram=False, seed=seed
    )
    real_axis = np.asarray(preferred.axis, dtype=float)
    real_list = preferred.axis
    real_score = preferred.rble_score

    neural_prescreen_axis = None
    neural_prescreen_sep = None
    try:
        from polomni.neural.scar_classifier.rble_scanner import predict_preferred_axis

        cmb, _, _ = load_real_sky_map(
            map_product_id=map_product_id, nside=nside, cache=cache
        )
        pred = predict_preferred_axis(cmb, checkpoint_dir=checkpoint_dir)
        if pred is not None:
            neural_prescreen_axis = pred.tolist()
            neural_prescreen_sep = align_sim_to_real(pred, real_axis)["separation_deg"]
    except Exception:
        pass

    arms: dict[str, ArmProbe] = {}
    # Discriminating open-loop arms (no hard real-axis feedback).
    arms["open_uniform"] = run_open_loop_toward_sky(
        real_axis=real_axis,
        steps=steps,
        nside=nside,
        seed=seed,
        policy=ChoicePolicy.UNIFORM,
        use_real_as_feedback=False,
    )
    arms["open_neural"] = run_open_loop_toward_sky(
        real_axis=real_axis,
        steps=steps,
        nside=nside,
        seed=seed,
        policy=ChoicePolicy.NEURAL,
        checkpoint_dir=checkpoint_dir,
        use_real_as_feedback=False,
    )
    # Telemetry: physics loops with observational feedback (often saturated).
    for name, policy in (
        ("physics_uniform", ChoicePolicy.UNIFORM),
        ("physics_neural", ChoicePolicy.NEURAL),
    ):
        result = run_physics_loop(
            steps=steps,
            nside=nside,
            map_product_id=map_product_id,
            cache=cache,
            seed=seed,
            policy=policy,
            checkpoint_dir=checkpoint_dir,
            neural_prescreen_real=policy == ChoicePolicy.NEURAL,
        )
        arms[name] = _arm_from_physics(name, result)

    improvement = (
        arms["open_uniform"].final_separation_deg - arms["open_neural"].final_separation_deg
    )
    neural_wins = improvement >= 5.0

    caveats = [
        "P1 CMB Radon scar was falsified on Planck holdout — this probe does not reopen it.",
        "Reference axis is hierarchical_sky_search on cached real CMB (provenance=real_cached_cmb).",
        "Win rule uses open-loop approach to that axis (no hard feedback).",
        "A neural win is interaction evidence, not a peer-reviewed multiverse detection.",
        "Preferred axes can be systematics; bubble/cross-sky instruments currently null.",
    ]
    if not guidance.ready:
        caveats.append("Graph-NODE checkpoints incomplete — open_neural degrades.")

    claim = (
        f"On {map_product_id} (nside={nside}), open-loop neural "
        f"{'beats' if neural_wins else 'does not beat'} open-loop uniform by "
        f"{improvement:+.2f}° final sep to hierarchical sky axis "
        f"(uniform {arms['open_uniform'].final_separation_deg:.2f}° → "
        f"neural {arms['open_neural'].final_separation_deg:.2f}°)."
    )

    return MultiverseProbeReport(
        map_product_id=map_product_id,
        nside=nside,
        steps=steps,
        real_axis=real_list,
        real_score=float(real_score),
        preferred_axis=preferred.to_dict(),
        neural_prescreen_axis=neural_prescreen_axis,
        neural_prescreen_sep_deg=neural_prescreen_sep,
        arms=arms,
        neural_beats_uniform=neural_wins,
        improvement_deg=float(improvement),
        claim=claim,
        caveats=caveats,
        guidance=guidance.status(),
    )


def write_probe_report(report: MultiverseProbeReport, path: Path | str) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return out
