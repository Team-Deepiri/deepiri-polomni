"""Integration tests for lab workflow orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import numpy as np
import pytest

from polomni.integration.benchmarks import run_benchmark_suite, time_rble_signature
from polomni.integration.workflow import WorkflowResult, run_lab_workflow
from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.downloader import FetchResult
from polomni.observatory.pipeline.sources.gwosc import GWCatalogSnapshot


def _mock_fetch(map_path):
    def _fetch(product, cache, **kwargs):
        return FetchResult(
            product_id=product.id,
            path=map_path,
            downloaded=False,
            bytes_written=map_path.stat().st_size,
            from_cache=True,
        )

    return _fetch


@pytest.mark.integration
def test_run_lab_workflow_mocked(tmp_path) -> None:
    """Mock network fetch and verify WorkflowResult structure."""
    map_path = tmp_path / "wmap_k_band.npy"
    np.save(map_path, synthetic_cmb_map(64, seed=11))

    cache = DataCache(root=tmp_path / "cache")
    gw_snap = GWCatalogSnapshot(
        fetched_at=datetime.now(timezone.utc),
        results_count=17,
        events=[],
    )

    with (
        patch("polomni.observatory.pipeline.processor.fetch_product", _mock_fetch(map_path)),
        patch(
            "polomni.observatory.pipeline.processor.fetch_gwtc_events",
            return_value=gw_snap,
        ),
        patch("polomni.observatory.pipeline.processor.load_cached_gwtc", return_value=None),
    ):
        result = run_lab_workflow(
            cache=cache,
            target_nside=64,
            null_ensemble=3,
            fetch_gw=True,
            simulation_choices=2,
        )

    assert isinstance(result, WorkflowResult)
    assert result.gw_count == 17
    assert result.simulation_summary["packets_spawned"] == 2
    assert result.simulation_summary["graph_nodes"] == 3
    assert result.pipeline_result.nside_used == 64
    assert result.pipeline_result.detection.rble_score >= 0.0

    payload = result.to_dict()
    assert payload["gw_count"] == 17
    assert "detection" in payload["pipeline"]
    assert payload["simulation_summary"]["choices_per_event"] == 2


@pytest.mark.integration
def test_benchmark_runs() -> None:
    """Benchmark helpers return timing metadata."""
    row = time_rble_signature(16, seed=0)
    assert row["nside"] == 16
    assert row["npix"] == 12 * 16 * 16
    assert row["seconds"] >= 0.0
    assert "rble_score" in row

    suite = run_benchmark_suite([16, 32])
    assert len(suite) == 2
    assert suite[0]["nside"] == 16
    assert suite[1]["nside"] == 32
