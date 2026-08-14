"""Tests for hierarchical sky search."""

import numpy as np

from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.scoring import hierarchical_search as hs
from polomni.observatory.scoring.hierarchical_search import hierarchical_sky_search
from polomni.observatory.scoring.rble_signature import inject_synthetic_scar


def test_hierarchical_search_finds_injected_scar() -> None:
    nside = 32
    axis = np.array([0.2, 0.3, 0.9])
    axis = axis / np.linalg.norm(axis)
    cmb = synthetic_cmb_map(nside, seed=1)
    scarred = inject_synthetic_scar(cmb, axis, amplitude=8.0)
    report = hierarchical_sky_search(scarred, coarse_nside=8, refine_samples=16, seed=0)
    assert report.rble_score > 1.0
    assert report.metadata.get("search") == "hierarchical"


class _FakeTomogram:
    score_integral = 2.0
    score_bifurcation = 1.0
    score_contrast = 0.5


def test_hierarchical_search_bonferroni_metadata(monkeypatch) -> None:
    """Bonferroni path unpacks (pass, sigma, alpha) and records metadata."""
    axis = np.array([0.2, 0.3, 0.9])
    axis = axis / np.linalg.norm(axis)

    monkeypatch.setattr(
        hs,
        "search_best_axis",
        lambda *a, **k: (axis, 3.5, {"coarse_axis": axis.tolist()}),
    )
    monkeypatch.setattr(hs, "build_radon_tomogram", lambda *a, **k: _FakeTomogram())

    cmb = synthetic_cmb_map(8, seed=1)
    report = hierarchical_sky_search(cmb, full_tomogram=True)

    meta = report.metadata
    assert meta["bonferroni_n_tests"] > 1
    assert meta["bonferroni_alpha"] < 0.05
    assert isinstance(meta["bonferroni_pass"], bool)
    assert meta["bonferroni_corrected_sigma"] < report.rble_score
    assert report.falsification_flags["bonferroni"] is meta["bonferroni_pass"]
