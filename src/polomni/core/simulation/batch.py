"""Batch district-graph simulations across RNG seeds."""

from __future__ import annotations

from polomni.core.superspace.district_graph import DistrictGraph


def run_batch_simulation(
    seeds: list[int],
    *,
    choices: int = 5,
    districts: int = 1,
) -> list[dict]:
    """Run district simulations for each seed and return summaries."""
    results: list[dict] = []
    for seed in seeds:
        graph = DistrictGraph()
        root_ids = []
        for i in range(districts):
            root_ids.append(
                graph.add_district(
                    mass=1.0 + 0.1 * i + seed * 1e-6,
                    law_of_gravity=[6.674e-11, 1.1e-52],
                    coordinate=[float(i + seed * 0.01), 0.0, 0.0],
                    lambda_vacuum=1.0e-52,
                )
            )
        packets = []
        for root in root_ids:
            packets.extend(graph.trigger_choice_event(root, num_choices=choices))
        results.append(
            {
                "seed": seed,
                "packets_spawned": len(packets),
                "graph_nodes": graph.graph.number_of_nodes(),
                "graph_edges": graph.graph.number_of_edges(),
                "choices": choices,
                "districts": districts,
            }
        )
    return results
