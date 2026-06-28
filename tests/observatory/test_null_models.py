"""Tests for null model tiers N0–N2."""

import numpy as np

from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.scoring.null_models import (
    NullTier,
    generate_grf_null,
    generate_rotation_shuffled_null,
    run_null_tier_comparison,
)


def test_grf_null_shape() -> None:
    maps = generate_grf_null(5, 16, seed=1)
    assert maps.shape == (5, 12 * 16 * 16)


def test_rotation_shuffled_preserves_rms() -> None:
    base = synthetic_cmb_map(16, seed=2)
    rotated = generate_rotation_shuffled_null(base, 3, seed=3)
    assert rotated.shape[0] == 3
    assert np.isclose(np.std(base), np.std(rotated[0]), rtol=0.15)


def test_null_tier_comparison_runs() -> None:
    cmb = synthetic_cmb_map(16, seed=4)
    result = run_null_tier_comparison(
        cmb,
        [NullTier.GRF, NullTier.ROTATION_SHUFFLED],
        n_ensemble=5,
        seed=5,
    )
    assert "score" in result
    assert "grf" in result["tiers"]
    assert "rotation_shuffled" in result["tiers"]
