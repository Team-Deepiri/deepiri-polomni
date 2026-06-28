"""Unit tests for omnifold_core.superspace.district_graph."""

from __future__ import annotations

import numpy as np
import pytest

from omnifold_core.superspace.district_graph import DistrictGraph


def test_add_district_increments_ids() -> None:
    graph = DistrictGraph()
    d0 = graph.add_district(1.0, [6.67e-11], [0.0, 0.0, 0.0], lambda_vacuum=1.1e-52)
    d1 = graph.add_district(2.0, [6.67e-11, 1.0], [1.0, 0.0, 0.0], lambda_vacuum=2.0e-52)

    assert d0 == 0
    assert d1 == 1
    assert graph.graph.nodes[d0]["mass"] == 1.0
    assert graph.graph.nodes[d1]["lambda_vacuum"] == pytest.approx(2.0e-52)


def test_trigger_choice_event_spawns_children_with_portals() -> None:
    graph = DistrictGraph(gravity_mutation_strength=0.1)
    parent = graph.add_district(
        mass=10.0,
        law_of_gravity=[1.0, 0.5],
        coordinate=[2.0, 3.0, 4.0],
        lambda_vacuum=0.01,
    )

    packets = graph.trigger_choice_event(parent, num_choices=3)

    assert len(packets) == 3
    assert all(p.parent_id == parent for p in packets)
    assert len({p.district_id for p in packets}) == 3

    weights = packets[0].branch_weights
    assert weights is not None
    assert sum(weights) == pytest.approx(1.0, rel=1e-9)

    child_ids = [p.district_id for p in packets]
    for child_id in child_ids:
        assert graph.graph.has_edge(parent, child_id)
        edge = graph.graph.edges[parent, child_id]
        np.testing.assert_allclose(edge["black_hole_at"], [2.0, 3.0, 4.0])

    g_parent = np.array([1.0, 0.5])
    g_child0 = graph.graph.nodes[child_ids[0]]["law_of_gravity"]
    g_child2 = graph.graph.nodes[child_ids[2]]["law_of_gravity"]
    assert np.linalg.norm(g_child0 - g_parent) < np.linalg.norm(g_child2 - g_parent)


def test_conductance_get_set() -> None:
    graph = DistrictGraph()
    parent = graph.add_district(1.0, [1.0], [0.0], lambda_vacuum=0.0)
    packets = graph.trigger_choice_event(parent, num_choices=2)
    child = packets[0].district_id

    initial = graph.get_conductance(parent, child)
    assert initial > 0.0

    graph.set_conductance(parent, child, 0.42)
    assert graph.get_conductance(parent, child) == pytest.approx(0.42)
    assert graph.get_conductance(child, parent) == 0.0


def test_to_dict_from_dict_roundtrip() -> None:
    graph = DistrictGraph(gravity_mutation_strength=0.2)
    root = graph.add_district(5.0, [1.0, 2.0], [0.5, 0.5], lambda_vacuum=0.1)
    graph.trigger_choice_event(root, num_choices=2)

    restored = DistrictGraph.from_dict(graph.to_dict())

    assert set(restored.graph.nodes) == set(graph.graph.nodes)
    assert set(restored.graph.edges) == set(graph.graph.edges)
    assert restored.gravity_mutation_strength == pytest.approx(0.2)

    for node in graph.graph.nodes:
        np.testing.assert_allclose(
            restored.graph.nodes[node]["law_of_gravity"],
            graph.graph.nodes[node]["law_of_gravity"],
        )
