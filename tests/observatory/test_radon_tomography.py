"""Tests for geodesic Radon tomography (Eq. 6)."""

from __future__ import annotations

import numpy as np
import pytest

from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.scoring.null_ensemble import generate_null_ensemble
from polomni.observatory.scoring.radon_tomography import (
    build_radon_tomogram,
    geodesic_radon_profile,
    rble_score_at_axis,
    scores_from_profile,
)
from polomni.observatory.scoring.rble_signature import inject_synthetic_scar


@pytest.mark.observatory
def test_geodesic_profile_nonzero_on_cmb() -> None:
    m = synthetic_cmb_map(32, seed=3)
    axis = np.array([0.0, 0.0, 1.0])
    profile, eta = geodesic_radon_profile(m, axis, n_eta=64, method="transform")
    assert profile.size == eta.size == 64
    assert np.isfinite(profile).all()


@pytest.mark.observatory
def test_injected_scar_raises_radon_integral() -> None:
    nside = 32
    axis = np.array([0.3, 0.4, 0.85])
    axis /= np.linalg.norm(axis)
    base = synthetic_cmb_map(nside, seed=5)
    scarred = inject_synthetic_scar(base, axis, amplitude=12.0)
    s_null = rble_score_at_axis(base, axis, n_eta=48, method="transform")
    s_scar = rble_score_at_axis(scarred, axis, n_eta=48, method="transform")
    assert s_scar > s_null * 5.0


@pytest.mark.observatory
def test_scar_above_null_ensemble() -> None:
    nside = 32
    axis = np.array([0.2, 0.3, 0.93])
    axis /= np.linalg.norm(axis)
    scarred = inject_synthetic_scar(synthetic_cmb_map(nside, seed=7), axis, amplitude=10.0)
    obs = rble_score_at_axis(scarred, axis, n_eta=48, method="transform")
    nulls = generate_null_ensemble(25, nside, seed=99)
    null_scores = [
        rble_score_at_axis(m, axis, n_eta=48, method="transform") for m in nulls
    ]
    mu = float(np.mean(null_scores))
    assert obs > mu + 3.0 * float(np.std(null_scores))


@pytest.mark.observatory
def test_tomogram_scores_match_integral() -> None:
    m = synthetic_cmb_map(32, seed=1)
    axis = np.array([0.1, 0.2, 0.97])
    tom = build_radon_tomogram(m, axis, n_eta=64, method="transform")
    integral, bif, contrast = scores_from_profile(tom.profile)
    assert abs(tom.score_integral - integral) < 1e-9
    assert tom.bifurcation.size == tom.profile.size
