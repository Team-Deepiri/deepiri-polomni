"""Unit tests for RBLE conservation laws."""

from __future__ import annotations

import math

import numpy as np
import pytest

from omnifold_core.conservation import (
    ConservationViolationError,
    assert_stream_entropy_closure,
    compute_information_trace,
    enforce_stream_entropy_closure,
    stream_flux_integral,
    stream_shannon_entropy,
)


class TestComputeInformationTrace:
    def test_2x2_diagonal_trace(self) -> None:
        # I = diag(0.6, 0.8) => Tr(I^2) = 0.36 + 0.64 = 1.0
        i_tensor = np.diag([0.6, 0.8])
        assert compute_information_trace(i_tensor) == pytest.approx(1.0)

    def test_4x4_identity_scaled(self) -> None:
        i_tensor = 0.5 * np.eye(4)
        # Tr((0.5 I)^2) = Tr(0.25 I) = 4 * 0.25 = 1.0
        assert compute_information_trace(i_tensor) == pytest.approx(1.0)

    def test_rejects_non_square(self) -> None:
        with pytest.raises(ValueError, match="2x2 or 4x4"):
            compute_information_trace(np.ones((2, 3)))

    def test_rejects_asymmetric(self) -> None:
        with pytest.raises(ValueError, match="symmetric"):
            compute_information_trace(np.array([[0.0, 1.0], [0.0, 0.0]]))


class TestStreamFluxIntegral:
    def test_uniform_five_branch_stream(self) -> None:
        phi = np.full(5, 0.2)
        # A_H = 4π, sum(phi) = 1.0 => flux = 4π
        area = 4.0 * math.pi
        assert stream_flux_integral(phi, area) == pytest.approx(4.0 * math.pi)

    def test_flux_scales_with_area(self) -> None:
        phi = np.array([0.3, 0.7])
        assert stream_flux_integral(phi, 2.0) == pytest.approx(2.0)
        assert stream_flux_integral(phi, 10.0) == pytest.approx(10.0)


class TestStreamShannonEntropy:
    def test_uniform_five_way_choice(self) -> None:
        phi = np.ones(5)
        assert stream_shannon_entropy(phi) == pytest.approx(math.log(5.0))

    def test_certain_branch_zero_entropy(self) -> None:
        phi = np.array([1.0, 0.0, 0.0])
        assert stream_shannon_entropy(phi) == pytest.approx(0.0)


class TestEnforceStreamEntropyClosure:
    def test_closed_stream_matches_trace(self) -> None:
        # Build I with Tr(I^2) = 1.25
        i_tensor = np.diag([0.5, 1.0])
        trace = compute_information_trace(i_tensor)
        assert trace == pytest.approx(1.25)

        # Choose phi so flux = 1.25 with A_H = 1
        phi = np.array([0.5, 0.75])
        assert stream_flux_integral(phi, 1.0) == pytest.approx(1.25)
        assert enforce_stream_entropy_closure(phi, trace, horizon_area=1.0)

    def test_open_stream_fails_closure(self) -> None:
        i_tensor = np.diag([1.0, 0.0])
        trace = compute_information_trace(i_tensor)
        phi = np.array([0.1, 0.1])
        assert not enforce_stream_entropy_closure(phi, trace, horizon_area=1.0)

    def test_assert_raises_on_violation(self) -> None:
        with pytest.raises(ConservationViolationError):
            assert_stream_entropy_closure(np.array([0.1]), information_tensor_trace=1.0)
