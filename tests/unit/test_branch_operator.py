"""Unit tests for omnifold_core.superspace.branch_operator."""

from __future__ import annotations

import numpy as np
import pytest

from omnifold_core.state.unified_state import UnifiedStateVector
from omnifold_core.superspace.branch_operator import BranchOperator


def test_compute_branch_weights_softmax_sums_to_one() -> None:
    op = BranchOperator()
    choice = np.array([0.2, 0.5, 0.9])
    weights = op.compute_branch_weights(choice, num_choices=3)

    assert weights.shape == (3,)
    assert np.all(weights > 0.0)
    assert weights.sum() == pytest.approx(1.0, rel=1e-12)
    assert weights[2] > weights[0]


def test_B_k_preserves_norm_and_differs_by_branch() -> None:
    op = BranchOperator()
    num_choices = 4
    psi = np.concatenate([np.ones(3), np.array([0.1, 0.2, 0.3, 0.4])])

    psi0 = op.B_k(psi, k=0, num_choices=num_choices)
    psi3 = op.B_k(psi, k=3, num_choices=num_choices)

    assert np.linalg.norm(psi0) == pytest.approx(1.0, rel=1e-9)
    assert np.linalg.norm(psi3) == pytest.approx(1.0, rel=1e-9)
    assert not np.allclose(psi0, psi3)


def test_B_k_batch_shape() -> None:
    op = BranchOperator()
    batch = np.vstack([np.ones(5), np.ones(5) * 2.0])
    out = op.B_k(batch, k=1, num_choices=2)

    assert out.shape == batch.shape
    assert np.linalg.norm(out[0]) == pytest.approx(1.0, rel=1e-9)


def test_split_state_vector_produces_one_hot_weighted_branches() -> None:
    op = BranchOperator()
    state = UnifiedStateVector(
        X_spatial=np.array([1.0, 0.0]),
        P_momentum=np.array([0.5]),
        Lambda_laws=np.array([0.01]),
        C_choice=np.array([0.1, 0.7, 0.2]),
    )

    branches = op.split_state_vector(state, num_choices=3)

    assert len(branches) == 3
    for k, branch in enumerate(branches):
        np.testing.assert_allclose(branch.X_spatial, state.X_spatial)
        assert branch.C_choice[k] > 0.0
        assert branch.C_choice.sum() == pytest.approx(
            op.compute_branch_weights(state.C_choice, 3)[k], rel=1e-9
        )

    total_weight = sum(b.C_choice.sum() for b in branches)
    assert total_weight == pytest.approx(1.0, rel=1e-9)
