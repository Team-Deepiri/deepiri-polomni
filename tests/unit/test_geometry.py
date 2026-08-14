"""Unit tests for unsigned-axis geometry helpers."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.core.geometry import (
    align_axis_to_reference,
    axis_separation_deg,
    coordinate_to_axis,
)


def test_axis_separation_treats_antipodes_as_zero() -> None:
    a = np.array([1.0, 0.0, 0.0])
    assert axis_separation_deg(a, a) == pytest.approx(0.0, abs=1e-4)
    assert axis_separation_deg(a, -a) == pytest.approx(0.0, abs=1e-4)


def test_align_axis_flips_antipode() -> None:
    ref = np.array([1.0, 0.0, 0.0])
    aligned, flipped = align_axis_to_reference([-1.0, 0.0, 0.0], ref)
    assert flipped is True
    assert aligned[0] == pytest.approx(1.0)
    assert axis_separation_deg(aligned, ref) == pytest.approx(0.0, abs=1e-4)


def test_align_axis_keeps_same_hemisphere() -> None:
    ref = np.array([0.0, 0.0, 1.0])
    aligned, flipped = align_axis_to_reference([0.1, 0.0, 0.9], ref)
    assert flipped is False
    assert aligned[2] > 0.0


def test_coordinate_to_axis_normalizes() -> None:
    axis = coordinate_to_axis([2.0, 0.0, 0.0])
    assert axis == pytest.approx(np.array([1.0, 0.0, 0.0]))
