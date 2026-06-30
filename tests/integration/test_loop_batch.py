"""Tests for loop batch corpus generation."""

from __future__ import annotations

from polomni.core.superspace.district_graph import ChoicePolicy
from polomni.integration.loop_batch import run_loop_batch
from polomni.integration.loop_logger import run_and_log_loop
from polomni.neural.datasets.loop_corpus import load_corpus
from polomni.observatory.scoring.axis_search import anisotropy_scores_batch, healpix_direction_grid
from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.scoring.rble_signature import inject_synthetic_scar
import numpy as np


def test_anisotropy_batch_matches_scalar() -> None:
    axis = np.array([0.1, 0.2, 0.97])
    axis /= np.linalg.norm(axis)
    cmb = synthetic_cmb_map(32, seed=0)
    scarred = inject_synthetic_scar(cmb, axis, amplitude=10.0)
    directions = healpix_direction_grid(4)[:8]
    batch = anisotropy_scores_batch(scarred, directions)
    assert batch.shape == (8,)
    assert float(np.max(batch)) > 0.0


def test_run_and_log_loop(tmp_path) -> None:
    _, results, path = run_and_log_loop(
        steps=2,
        nside=16,
        seed=1,
        policy=ChoicePolicy.UNIFORM,
        output_dir=tmp_path,
    )
    assert path.exists()
    assert len(results) == 2


def test_loop_batch(tmp_path) -> None:
    batch = run_loop_batch(
        count=2,
        steps=1,
        nside=16,
        base_seed=0,
        output_dir=tmp_path,
        workers=1,
    )
    assert batch.n_runs == 2
    corpus = load_corpus(tmp_path)
    assert corpus.n_samples >= 2
