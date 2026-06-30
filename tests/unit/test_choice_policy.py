"""Unit tests for choice policies and simulation chains."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.core.superspace.district_graph import ChoicePolicy, DistrictGraph


def test_uniform_policy_sums_to_one() -> None:
    graph = DistrictGraph()
    root = graph.add_district(1.0, [1.0, 1e-52], [0, 0, 1], 1e-52)
    packets = graph.trigger_choice_event(root, 5, policy=ChoicePolicy.UNIFORM)
    w = packets[0].branch_weights
    assert sum(w) == pytest.approx(1.0)
    assert len(set(w)) == 1


def test_axis_biased_non_uniform() -> None:
    graph = DistrictGraph()
    root = graph.add_district(1.0, [1.0, 1e-52], [0, 0, 1], 1e-52)
    packets = graph.trigger_choice_event(
        root, 4, policy=ChoicePolicy.AXIS_BIASED, bias_axis=[0, 0, 1]
    )
    weights = packets[0].branch_weights
    assert max(weights) != min(weights)


def test_simulation_chain_grows_graph() -> None:
    graph = DistrictGraph()
    root = graph.add_district(1.0, [1.0, 1e-52], [0, 0, 1], 1e-52)
    packets = graph.run_simulation_chain(steps=3, num_choices=3)
    assert len(packets) == 9
    assert graph.graph.number_of_nodes() > 3
