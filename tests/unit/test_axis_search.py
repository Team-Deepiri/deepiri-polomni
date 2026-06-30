"""Unit tests for optimized axis search."""

from __future__ import annotations

import numpy as np

from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.scoring.axis_search import PreparedCmbMap, search_best_axis
from polomni.observatory.scoring.rble_signature import inject_synthetic_scar


def test_prepared_map_search_recovers_injected_axis() -> None:
    axis = np.array([0.2, 0.3, 0.93])
    axis /= np.linalg.norm(axis)
    cmb = synthetic_cmb_map(32, seed=0)
    scarred = inject_synthetic_scar(cmb, axis, amplitude=12.0)
    prepared = PreparedCmbMap.from_map(scarred)
    found, score, _ = search_best_axis(prepared, dir_nside=8, refine_samples=12, seed=1)
    dot = abs(float(np.dot(found / np.linalg.norm(found), axis)))
    assert score > 0.1
    assert float(np.degrees(np.arccos(dot))) < 20.0
