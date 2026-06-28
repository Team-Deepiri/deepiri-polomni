"""Unit tests for information stress tensor."""

import numpy as np

from polomni.core.gravity.information_tensor import information_tensor_N, trace_I_squared


def test_information_tensor_ln_n_scaling() -> None:
    i5 = information_tensor_N(5, np.zeros(4))
    i1 = information_tensor_N(1, np.zeros(4))
    assert trace_I_squared(i5) > trace_I_squared(i1)


def test_trace_I_squared_known_diagonal() -> None:
    i = np.diag([1.0, 2.0, 3.0, 4.0])
    assert trace_I_squared(i) == pytest.approx(30.0, rel=1e-12)


def test_information_tensor_shape() -> None:
    i = information_tensor_N(3, np.array([0.1, 0.2]))
    assert i.shape == (4, 4)


import pytest  # noqa: E402
