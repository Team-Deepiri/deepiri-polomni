"""Unit tests for closed-loop scan feedback (no full CMB search)."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.core.geometry import axis_separation_deg, coordinate_to_axis
from polomni.core.superspace.district_graph import DistrictGraph
from polomni.integration.closed_loop import apply_scan_feedback
from polomni.observatory.scoring.rble_signature import DetectionReport


def _detection(axis: list[float]) -> DetectionReport:
    a = np.asarray(axis, dtype=float)
    a = a / (np.linalg.norm(a) + 1e-15)
    return DetectionReport(
        rble_score=1.0,
        preferred_axis=a.tolist(),
        n_hat=a.tolist(),
    )


def test_feedback_antipode_does_not_worsen_axis_error() -> None:
    """Recovered −x must pull toward +x, not shrink the parent coordinate."""
    graph = DistrictGraph(gravity_mutation_strength=0.05)
    root = graph.add_district(
        mass=1.0,
        law_of_gravity=[1.0, 0.0],
        coordinate=[1.0, 0.0, 0.0],
        lambda_vacuum=1e-3,
    )
    before = coordinate_to_axis(graph.graph.nodes[root]["coordinate"])
    antipode = [-1.0, 0.0, 0.0]
    # Unsigned error before feedback is ~0° (same axis).
    assert axis_separation_deg(before, antipode) == pytest.approx(0.0, abs=1e-4)

    applied = apply_scan_feedback(
        graph,
        _detection(antipode),
        parent_id=root,
        mode="coordinate_shift",
        learning_rate=0.15,
    )
    after = coordinate_to_axis(graph.graph.nodes[root]["coordinate"])

    assert applied["antipode_aligned"] is True
    assert applied["axis_error_deg_before"] == pytest.approx(0.0, abs=1e-3)
    assert applied["axis_error_deg_after"] == pytest.approx(0.0, abs=1e-3)
    # Stay on +x hemisphere; do not rotate toward −x.
    assert after[0] > 0.99
    assert axis_separation_deg(before, after) < 1.0


def test_feedback_same_hemisphere_still_shifts() -> None:
    graph = DistrictGraph()
    root = graph.add_district(
        mass=1.0,
        law_of_gravity=[1.0, 0.0],
        coordinate=[1.0, 0.0, 0.0],
        lambda_vacuum=1e-3,
    )
    target = [0.0, 1.0, 0.0]
    applied = apply_scan_feedback(
        graph,
        _detection(target),
        parent_id=root,
        mode="coordinate_shift",
        learning_rate=0.2,
    )
    assert applied["antipode_aligned"] is False
    after = np.asarray(graph.graph.nodes[root]["coordinate"], dtype=float)
    assert after[1] > 0.0
    assert applied["axis_error_deg_after"] < applied["axis_error_deg_before"]
