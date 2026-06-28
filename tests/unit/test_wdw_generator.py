"""Unit tests for omnifold_core.superspace.wdw_generator."""

from __future__ import annotations

import numpy as np
import pytest

from omnifold_core.state.stream_packet import StreamPacket
from omnifold_core.state.unified_state import UnifiedStateVector
from omnifold_core.superspace.wdw_generator import WDWGenerator


def test_spawn_wavepackets_count_and_metric_mutation() -> None:
    gen = WDWGenerator(metric_mutation_scale=0.2)
    phi = np.array([1.0, 2.0, 3.0])

    packets = gen.spawn_wavepackets(num_choices=3, phi_stream=phi)

    assert len(packets) == 3
    assert packets[0].metric_mutation.shape == (3, 3)
    assert packets[2].metric_mutation[0, 0] > packets[0].metric_mutation[0, 0]
    assert packets[1].momentum_vector[1] == pytest.approx(2.0)


def test_inject_stream_minimizes_residual_against_phi() -> None:
    gen = WDWGenerator()
    phi = np.array([0.5, -0.25])
    parent = UnifiedStateVector(
        X_spatial=np.zeros(2),
        P_momentum=np.array([0.1, 0.0]),
        Lambda_laws=np.array([0.01]),
        C_choice=np.array([0.3, 0.7]),
    )
    packet = StreamPacket(
        district_id=1,
        parent_id=0,
        num_choices=2,
        phi_stream=phi.tolist(),
        information_trace=1.0,
        branch_weights=[0.6, 0.4],
    )

    injected = gen.inject_stream(packet, parent)

    assert len(injected) == 2
    for wp in injected:
        np.testing.assert_allclose(wp.momentum_vector, phi, rtol=1e-9, atol=1e-9)
        assert wp.stream_residual == pytest.approx(0.0, abs=1e-12)


def test_inject_stream_uses_branch_weights() -> None:
    gen = WDWGenerator()
    phi = np.array([1.0, 0.5])
    parent = UnifiedStateVector(
        X_spatial=np.zeros(1),
        P_momentum=np.array([0.0, 0.0]),
        Lambda_laws=np.array([0.0]),
        C_choice=np.array([0.5, 0.5]),
    )
    packet = StreamPacket(
        district_id=2,
        parent_id=1,
        num_choices=2,
        phi_stream=phi.tolist(),
        information_trace=0.5,
        branch_weights=[0.9, 0.1],
    )

    injected = gen.inject_stream(packet, parent)
    assert injected[0].branch_id == 0
    assert injected[1].branch_id == 1
