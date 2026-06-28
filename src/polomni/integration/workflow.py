"""End-to-end lab workflow: ingest → district simulation → RBLE pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from polomni.core.superspace.district_graph import DistrictGraph
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.processor import PipelineResult, ingest_standard_data, run_rble_pipeline


@dataclass
class WorkflowResult:
    """Combined output from ingest, simulation, and observatory pipeline."""

    simulation_summary: dict[str, Any]
    pipeline_result: PipelineResult
    gw_count: int

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable summary (excludes heavy ingest payloads)."""
        det = self.pipeline_result.detection
        return {
            "simulation_summary": self.simulation_summary,
            "gw_count": self.gw_count,
            "pipeline": {
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
            },
        }


def _run_short_simulation(*, choices: int = 3) -> dict[str, Any]:
    """Run a minimal district-graph RBLE simulation."""
    graph = DistrictGraph(gravity_mutation_strength=0.05)
    root = graph.add_district(
        mass=1.0,
        law_of_gravity=[6.674e-11, 1.1e-52],
        coordinate=[0.0, 0.0, 0.0],
        lambda_vacuum=1.0e-52,
    )
    packets = graph.trigger_choice_event(root, num_choices=choices)
    return {
        "root_district": root,
        "choices_per_event": choices,
        "packets_spawned": len(packets),
        "graph_nodes": graph.graph.number_of_nodes(),
        "graph_edges": graph.graph.number_of_edges(),
        "mean_phi_stream": float(
            sum(sum(p.phi_stream) / len(p.phi_stream) for p in packets) / max(len(packets), 1)
        ),
    }


def run_lab_workflow(
    *,
    cache: DataCache | None = None,
    target_nside: int = 64,
    null_ensemble: int = 10,
    fetch_gw: bool = True,
    simulation_choices: int = 3,
) -> WorkflowResult:
    """Ingest standard data, simulate district branching, run RBLE pipeline."""
    cache = cache or DataCache()

    ingest = ingest_standard_data(cache, fetch_gw=fetch_gw)
    gw_count = ingest.gw_snapshot.results_count if ingest.gw_snapshot is not None else 0

    simulation_summary = _run_short_simulation(choices=simulation_choices)

    pipeline_result = run_rble_pipeline(
        cache=cache,
        target_nside=target_nside,
        null_ensemble=null_ensemble,
        fetch_gw=fetch_gw,
    )

    return WorkflowResult(
        simulation_summary=simulation_summary,
        pipeline_result=pipeline_result,
        gw_count=gw_count,
    )
