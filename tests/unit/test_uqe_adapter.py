"""Unit tests for UQE bridge adapter."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.bridge.uqe_adapter import (
    apply_uqe_conductance_to_graph,
    density_matrices_from_branch_weights,
    uqe_bridge_from_simulation,
)
from polomni.core.superspace.district_graph import DistrictGraph


def test_density_matrices_trace_to_one() -> None:
    mats = density_matrices_from_branch_weights([0.6, 0.4], dim=2)
    for rho in mats:
        assert float(np.trace(rho).real) == pytest.approx(1.0, rel=1e-6)


def test_uqe_updates_conductance() -> None:
    graph = DistrictGraph()
    root = graph.add_district(1.0, [1.0, 1e-52], [0, 0, 1], 1e-52)
    packets = graph.trigger_choice_event(root, 3)
    before = [graph.get_conductance(root, c) for c in graph.graph.successors(root)]
    result = uqe_bridge_from_simulation(graph, packets, root)
    after = [graph.get_conductance(root, c) for c in graph.graph.successors(root)]
    assert result["updated"] == 3
    assert before != after
