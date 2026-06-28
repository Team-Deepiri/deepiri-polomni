"""Unit tests for UnifiedStateVector and related state types."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.core.state.choice_event import ChoiceEvent
from polomni.core.state.stream_packet import StreamPacket
from polomni.core.state.unified_state import UnifiedStateVector


class TestUnifiedStateVector:
    def test_psi_stacks_blocks_in_order(self) -> None:
        state = UnifiedStateVector(
            X_spatial=np.array([1.0, 2.0]),
            P_momentum=np.array([3.0]),
            Lambda_laws=np.array([4.0, 5.0, 6.0]),
            C_choice=np.array([7.0, 8.0]),
            t=1.5,
        )
        expected = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        assert np.allclose(state.Psi, expected)
        assert state.dim == 8
        assert state.t == pytest.approx(1.5)

    def test_norm_and_normalize(self) -> None:
        state = UnifiedStateVector(
            X_spatial=np.array([3.0, 0.0]),
            P_momentum=np.array([4.0]),
            Lambda_laws=np.array([]),
            C_choice=np.array([]),
        )
        assert state.norm() == pytest.approx(5.0)
        unit = state.normalize()
        assert unit.norm() == pytest.approx(1.0)
        assert unit.X_spatial[0] == pytest.approx(0.6)
        assert unit.P_momentum[0] == pytest.approx(0.8)

    def test_with_time_preserves_components(self) -> None:
        state = UnifiedStateVector(
            X_spatial=np.array([1.0]),
            P_momentum=np.array([2.0]),
            Lambda_laws=np.array([3.0]),
            C_choice=np.array([4.0]),
            t=0.0,
        )
        advanced = state.with_time(42.0)
        assert advanced.t == pytest.approx(42.0)
        assert np.allclose(advanced.Psi, state.Psi)

    def test_invalidate_cache_after_mutation(self) -> None:
        state = UnifiedStateVector(
            X_spatial=np.array([1.0]),
            P_momentum=np.array([0.0]),
            Lambda_laws=np.array([0.0]),
            C_choice=np.array([0.0]),
        )
        _ = state.Psi
        state.X_spatial[0] = 9.0
        state.invalidate_cache()
        assert state.Psi[0] == pytest.approx(9.0)


class TestStreamPacket:
    def test_normalizes_branch_weights(self) -> None:
        packet = StreamPacket(
            district_id=0,
            parent_id=None,
            num_choices=3,
            phi_stream=[0.2, 0.3, 0.5],
            information_trace=1.0,
            branch_weights=[2.0, 2.0, 6.0],
        )
        assert sum(packet.branch_weights) == pytest.approx(1.0)
        assert packet.branch_weights[2] == pytest.approx(0.6)

    def test_shannon_entropy_uniform_weights(self) -> None:
        packet = StreamPacket(
            district_id=0,
            parent_id=None,
            num_choices=3,
            phi_stream=[1.0, 1.0, 1.0],
            information_trace=1.0,
            branch_weights=[1.0, 1.0, 1.0],
        )
        assert packet.shannon_entropy() == pytest.approx(np.log(3.0), rel=1e-6)


class TestChoiceEvent:
    def test_information_spike_ln_n(self) -> None:
        event = ChoiceEvent(district_id=1, num_choices=5, t_choice=0.01)
        assert event.information_spike == pytest.approx(np.log(5.0))

    def test_rejects_mismatched_log_odds(self) -> None:
        with pytest.raises(ValueError, match="branch_log_odds"):
            ChoiceEvent(
                district_id=0,
                num_choices=3,
                t_choice=0.0,
                branch_log_odds=(0.1, 0.2),
            )
