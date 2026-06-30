"""Unit tests for GW phase correlation and conductance wiring."""

from __future__ import annotations

import numpy as np

from polomni.core.conductance.gw_correlation import (
    build_synthetic_gw_test,
    correlate_gw_phases,
    phase_correlation,
    synthetic_ringdown_phases,
    wire_gw_to_conductance,
)
from polomni.core.superspace.district_graph import DistrictGraph
from polomni.observatory.pipeline.sources.gwosc import GWEvent


def test_linked_phases_correlate_higher() -> None:
    events = [
        GWEvent(name="a", gps=1.0, catalog="t", detectors=["H1"]),
        GWEvent(name="b", gps=2.0, catalog="t", detectors=["L1"]),
    ]
    phases = synthetic_ringdown_phases(events, seed=0)
    phases["b"] = phases["a"] + 0.01
    stats = correlate_gw_phases(events, phases, [("a", "b")], [("a", "b")])
    assert stats["linked_mean"] > 0.9


def test_wire_gw_boosts_conductance() -> None:
    graph = DistrictGraph()
    root = graph.add_district(1.0, [1.0, 1e-52], [0, 0, 1], 1e-52)
    graph.trigger_choice_event(root, 2)
    child = list(graph.graph.successors(root))[0]
    old = graph.get_conductance(root, child)
    wire_gw_to_conductance(graph, [{"name": "GW1", "separation_deg": 5.0}])
    assert graph.get_conductance(root, child) > old


def test_build_synthetic_gw_test() -> None:
    graph = DistrictGraph()
    root = graph.add_district(1.0, [1.0, 1e-52], [0, 0, 1], 1e-52)
    graph.trigger_choice_event(root, 2)
    out = build_synthetic_gw_test(graph, ["GW1", "GW2", "GW3"], seed=1)
    assert "stats" in out
