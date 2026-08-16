"""Unit tests for the RBLE observatory pipeline processor.

These tests stub every network and heavy-compute edge of
``run_rble_pipeline`` so the pipeline can run fully offline and fast.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.downloader import FetchResult
from polomni.observatory.pipeline.events import EventLog
from polomni.observatory.pipeline.processor import IngestResult, run_rble_pipeline
from polomni.observatory.scoring.rble_signature import DetectionReport


def _fake_fetch(tmp_path: Path) -> FetchResult:
    return FetchResult(
        product_id="wmap_k_band",
        path=tmp_path / "map.fits",
        downloaded=False,
        bytes_written=0,
        from_cache=True,
    )


def _install_processor_mocks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    signature: Any,
) -> None:
    """Stub all network and heavy-compute edges of ``run_rble_pipeline``."""
    base = "polomni.observatory.pipeline.processor"

    monkeypatch.setattr(
        f"{base}.ingest_standard_data", lambda *a, **k: IngestResult()
    )
    monkeypatch.setattr(
        f"{base}.fetch_product",
        lambda product, cache, force=False: _fake_fetch(tmp_path),
    )
    monkeypatch.setattr(
        f"{base}.load_healpix_map",
        lambda path, field=None: np.arange(12, dtype=float),
    )
    monkeypatch.setattr(f"{base}.downsample_map", lambda m, nside: m.copy())
    monkeypatch.setattr(
        f"{base}.string_landscape_filter", lambda m, w_params: m + 100.0
    )
    monkeypatch.setattr(
        f"{base}.inverse_radon_bifurcation_filter",
        lambda m, angles: m + 1000.0,
    )
    monkeypatch.setattr(
        f"{base}.generate_null_ensemble", lambda n, nside, seed: []
    )
    monkeypatch.setattr(f"{base}.correlate_gw_rble", lambda *a, **k: [])
    monkeypatch.setattr(f"{base}.compute_rble_signature", signature)


def _run_mocked_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signature: Any,
) -> tuple[Any, EventLog]:
    _install_processor_mocks(monkeypatch, tmp_path, signature)
    cache = DataCache(tmp_path / "cache")
    log = EventLog(tmp_path / "events.jsonl")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = run_rble_pipeline(
            cache=cache,
            target_nside=1,
            null_ensemble=0,
            event_log=log,
            fetch_gw=False,
            enable_p1_pipeline=True,
        )
    return result, log


@pytest.mark.observatory
def test_rble_pipeline_emits_single_score_start_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only one ``score_start`` event should be logged per pipeline run."""
    def signature(m: np.ndarray) -> DetectionReport:
        return DetectionReport(
            rble_score=1.0,
            preferred_axis=[0.0, 0.0, 1.0],
            n_hat=[0.0, 0.0, 1.0],
        )

    result, log = _run_mocked_pipeline(tmp_path, monkeypatch, signature)

    score_starts = [e for e in log.read_all() if e.kind == "score_start"]
    assert len(score_starts) == 1
    assert result.detection.rble_score == 1.0


@pytest.mark.observatory
def test_rble_pipeline_detection_scores_the_filtered_map(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Detection must be computed on the P1-filtered map, exactly once."""
    captured: list[np.ndarray] = []

    def signature(m: np.ndarray) -> DetectionReport:
        captured.append(np.asarray(m, dtype=float).copy())
        return DetectionReport(
            rble_score=1.0,
            preferred_axis=[0.0, 0.0, 1.0],
            n_hat=[0.0, 0.0, 1.0],
            fnl_proxy=float(np.mean(m)),
        )

    result, _ = _run_mocked_pipeline(tmp_path, monkeypatch, signature)

    filtered = np.arange(12, dtype=float) + 100.0 + 1000.0
    assert result.detection.fnl_proxy == pytest.approx(float(np.mean(filtered)))
    assert len(captured) == 1
