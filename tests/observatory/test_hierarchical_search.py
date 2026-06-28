"""Tests for hierarchical sky search."""

import numpy as np

from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
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
