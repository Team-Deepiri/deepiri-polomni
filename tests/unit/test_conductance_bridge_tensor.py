"""Unit tests for ER=EPR bridge conductance."""

import networkx as nx
import numpy as np

from polomni.core.conductance.bridge_tensor import bridge_conductance, conductance_matrix


def test_bridge_conductance_exponential_suppression() -> None:
    g_low = bridge_conductance(0.0, np.array([1.0]), np.array([1.0]), 1.0)
    g_high = bridge_conductance(5.0, np.array([1.0]), np.array([1.0]), 1.0)
    assert g_low > g_high


def test_bridge_conductance_orthogonal_streams_zero() -> None:
    g = bridge_conductance(0.0, np.array([1.0, 0.0]), np.array([0.0, 1.0]), 1.0)
    assert g == pytest.approx(0.0, abs=1e-12)


def test_conductance_matrix_from_graph() -> None:
    g = nx.DiGraph()
    g.add_edge(0, 1, conductance=0.5)
    g.add_edge(1, 2, conductance=0.25)
    mat = conductance_matrix(g)
    assert mat.shape == (3, 3)
    assert mat[0, 1] == pytest.approx(0.5, rel=1e-9)
    assert mat[1, 2] == pytest.approx(0.25, rel=1e-9)


import pytest  # noqa: E402
