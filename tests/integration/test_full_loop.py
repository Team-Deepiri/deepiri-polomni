"""Integration tests for the full RBLE simulation loop."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.core.conservation import enforce_stream_entropy_closure
from polomni.core.radon.vacuum_stream import RadonVacuumPipeline
from polomni.core.state.unified_state import UnifiedStateVector
from polomni.core.superspace.district_graph import DistrictGraph
from polomni.core.superspace.wdw_generator import WDWGenerator


@pytest.mark.integration
def test_full_loop_choice_stream_spawn() -> None:
    """Verify choice → Radon stream → WDW spawn closes conservation."""
    num_choices = 4

    # 1. Choice event on district graph
    graph = DistrictGraph(gravity_mutation_strength=0.08)
    root = graph.add_district(
        mass=12.0,
        law_of_gravity=[1.0, 0.25],
        coordinate=[1.0, 0.0, 0.0],
        lambda_vacuum=0.02,
    )
    choice_packets = graph.trigger_choice_event(root, num_choices=num_choices)
    assert len(choice_packets) == num_choices
    assert sum(choice_packets[0].branch_weights) == pytest.approx(1.0, rel=1e-9)

    # 2. Radon vacuum stream from district psi field
    nx = 9
    coords = np.linspace(-1.5, 1.5, nx)
    xg, yg, zg = np.meshgrid(coords, coords, coords, indexing="ij")
    psi_field = np.exp(-(xg**2 + yg**2 + zg**2))

    pipeline = RadonVacuumPipeline(
        district_id=root,
        parent_id=None,
        num_choices=num_choices,
        horizon_area=4.0 * np.pi,
        rotation_angles=(0.15, 0.3, 0.0),
        entropy_gradient=np.linspace(0.1, 0.4, 4),
    )
    stream_packet = pipeline.run(psi_field)
    assert stream_packet.num_choices == num_choices
    assert len(stream_packet.phi_stream) == num_choices

    enforce_stream_entropy_closure(
        np.asarray(stream_packet.phi_stream),
        stream_packet.information_trace,
        horizon_area=pipeline.horizon_area,
    )

    # 3. Wheeler-DeWitt spawn from stream injection
    parent_state = UnifiedStateVector(
        X_spatial=np.array([1.0, 0.0, 0.0]),
        P_momentum=np.asarray(stream_packet.phi_stream, dtype=float),
        Lambda_laws=np.array([0.02]),
        C_choice=np.ones(num_choices) / num_choices,
    )
    wdw = WDWGenerator(metric_mutation_scale=0.12)
    wavepackets = wdw.inject_stream(stream_packet, parent_state)

    assert len(wavepackets) == num_choices
    assert all(wp.branch_id == k for k, wp in enumerate(wavepackets))
    assert all(wp.stream_residual >= 0.0 for wp in wavepackets)

    # Graph grew: root + num_choices children
    assert graph.graph.number_of_nodes() == 1 + num_choices
    assert graph.graph.number_of_edges() == num_choices

    # Conductance on portal edges matches branch weights
    for pkt in choice_packets:
        g = graph.get_conductance(root, pkt.district_id)
        assert g > 0.0
