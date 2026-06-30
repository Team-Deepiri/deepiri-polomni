"""End-to-end lab workflow: closed loop + subsystem integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from polomni.bridge.uqe_adapter import uqe_bridge_from_simulation
from polomni.core.conductance.gw_correlation import build_synthetic_gw_test, wire_gw_to_conductance
from polomni.core.inflation.sky_patches import deff_fnl_from_simulation
from polomni.core.superspace.district_graph import ChoicePolicy, DistrictGraph
from polomni.integration.closed_loop import LoopStepResult, run_closed_loop
from polomni.neural.graph_node.training import train_graph_node_on_history
from polomni.neural.pinn.metric_solver import MetricPINN
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.processor import (
    PipelineResult,
    correlate_gw_rble,
    ingest_standard_data,
    run_rble_pipeline,
)
from polomni.observatory.pipeline.sources.gwosc import GWEvent


@dataclass
class WorkflowResult:
    """Combined output from ingest, simulation, and observatory pipeline."""

    simulation_summary: dict[str, Any]
    pipeline_result: PipelineResult | None
    gw_count: int
    closed_loop: list[dict[str, Any]] = field(default_factory=list)
    subsystems: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable summary."""
        payload: dict[str, Any] = {
            "simulation_summary": self.simulation_summary,
            "gw_count": self.gw_count,
            "closed_loop": self.closed_loop,
            "subsystems": self.subsystems,
        }
        if self.pipeline_result is not None:
            det = self.pipeline_result.detection
            payload["pipeline"] = {
                "map_product_id": self.pipeline_result.map_product_id,
                "map_path": str(self.pipeline_result.map_path),
                "nside_used": self.pipeline_result.nside_used,
                "planck_lambda": self.pipeline_result.planck_lambda,
                "report_path": (
                    str(self.pipeline_result.report_path)
                    if self.pipeline_result.report_path
                    else None
                ),
                "detection": det.model_dump(mode="json"),
            }
        return payload


def run_subsystem_suite(
    graph: DistrictGraph,
    packets: list,
    parent_id: int,
    *,
    nside: int = 32,
    last_detection_axis: list[float] | None = None,
) -> dict[str, Any]:
    """Run Path C subsystem integrations on a simulation state."""
    inflation = deff_fnl_from_simulation(graph, packets, nside=nside)
    neural = train_graph_node_on_history(graph, epochs=20)
    pinn = MetricPINN().fit(
        np.array([[0.0, 1.0, 0.5, 0.0], [0.0, 2.0, 1.0, 0.0]]),
        choice_entropy=0.8,
        epochs=15,
    )
    uqe = uqe_bridge_from_simulation(graph, packets, parent_id)

    gw_stats: dict[str, Any] = {"status": "skipped"}
    if last_detection_axis is not None:
        events = [
            GWEvent(name="GW_SYN_1", gps=1.0e9, catalog="synthetic", detectors=["H1", "L1"]),
            GWEvent(name="GW_SYN_2", gps=1.0e9 + 1, catalog="synthetic", detectors=["H1", "V1"]),
            GWEvent(name="GW_SYN_3", gps=1.0e9 + 2, catalog="synthetic", detectors=["L1", "V1"]),
        ]
        matches = correlate_gw_rble(last_detection_axis, events, max_separation_deg=90.0)
        wire_gw_to_conductance(graph, matches)
        gw_stats = build_synthetic_gw_test(
            graph, [e.name for e in events], seed=7
        )
        gw_stats["gw_matches"] = len(matches)

    return {
        "inflation": {
            "mean_deff": inflation["mean_deff"],
            "std_deff": inflation["std_deff"],
            "fnl_range": inflation["fnl_range"],
            "nside": inflation["nside"],
        },
        "neural": neural,
        "pinn": {k: v for k, v in pinn.items() if k != "loss_history"},
        "uqe_bridge": uqe,
        "gw_correlation": gw_stats,
        "graph_export": graph.to_dict(),
    }


def run_lab_workflow(
    *,
    cache: DataCache | None = None,
    target_nside: int = 64,
    null_ensemble: int = 10,
    fetch_gw: bool = True,
    simulation_choices: int = 4,
    closed_loop_steps: int = 3,
    policy: ChoicePolicy = ChoicePolicy.AXIS_BIASED,
    use_real_data_pipeline: bool = False,
    seed: int = 0,
) -> WorkflowResult:
    """Run closed RBLE loop with subsystem suite; optional real-data pipeline."""
    cache = cache or DataCache()
    gw_count = 0

    if use_real_data_pipeline:
        ingest = ingest_standard_data(cache, fetch_gw=fetch_gw)
        gw_count = ingest.gw_snapshot.results_count if ingest.gw_snapshot is not None else 0
        pipeline_result = run_rble_pipeline(
            cache=cache,
            target_nside=target_nside,
            null_ensemble=null_ensemble,
            fetch_gw=fetch_gw,
        )
    else:
        pipeline_result = None

    graph, loop_results = run_closed_loop(
        steps=closed_loop_steps,
        num_choices=simulation_choices,
        nside=target_nside,
        seed=seed,
        policy=policy,
    )

    root = 0
    packets = graph.run_simulation_chain(
        steps=1,
        num_choices=simulation_choices,
        policy=policy,
    )
    last_axis = loop_results[-1].recovered_axis if loop_results else None
    subsystems = run_subsystem_suite(
        graph, packets, root, nside=min(32, target_nside), last_detection_axis=last_axis
    )

    simulation_summary = {
        "mode": "closed_loop",
        "choices_per_event": simulation_choices,
        "closed_loop_steps": closed_loop_steps,
        "policy": policy.value,
        "graph_nodes": graph.graph.number_of_nodes(),
        "graph_edges": graph.graph.number_of_edges(),
        "final_axis_error_deg": loop_results[-1].axis_error_deg if loop_results else None,
        "mean_rble_score": float(np.mean([r.rble_score for r in loop_results]))
        if loop_results
        else 0.0,
    }

    return WorkflowResult(
        simulation_summary=simulation_summary,
        pipeline_result=pipeline_result,
        gw_count=gw_count,
        closed_loop=[r.to_dict() for r in loop_results],
        subsystems=subsystems,
    )
