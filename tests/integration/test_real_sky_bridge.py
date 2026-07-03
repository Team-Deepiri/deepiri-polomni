"""Integration tests for real-sky physics bridge."""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest

from polomni.integration.real_sky_bridge import (
    PhysicsLoopResult,
    align_sim_to_real,
    run_physics_loop,
    scan_real_sky_axis,
)
from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.downloader import FetchResult


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


def _cache_with_map(tmp_path, nside: int = 64, seed: int = 11) -> DataCache:
    map_path = tmp_path / "wmap_k_band.npy"
    np.save(map_path, synthetic_cmb_map(nside, seed=seed))
    cache = DataCache(root=tmp_path / "cache")
    cache.record("wmap_k_band", map_path, url="file://mock")
    return cache


@pytest.mark.integration
def test_scan_real_sky_axis_mocked(tmp_path) -> None:
    cache = _cache_with_map(tmp_path)
    axis, score = scan_real_sky_axis(cache, "wmap_k_band", nside=64)
    assert axis.shape == (3,)
    assert np.isclose(np.linalg.norm(axis), 1.0, atol=1e-6)
    assert score >= 0.0


@pytest.mark.integration
def test_align_sim_to_real() -> None:
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([1.0, 0.0, 0.0])
    aligned = align_sim_to_real(a, b)
    assert aligned["separation_deg"] == pytest.approx(0.0, abs=1e-5)
    assert aligned["alignment_quality"] == pytest.approx(1.0, abs=1e-6)

    c = np.array([0.0, 1.0, 0.0])
    orthogonal = align_sim_to_real(a, c)
    assert orthogonal["separation_deg"] == pytest.approx(90.0, abs=1e-6)
    assert orthogonal["alignment_quality"] == pytest.approx(0.0, abs=1e-6)


@pytest.mark.integration
def test_run_physics_loop_mocked(tmp_path) -> None:
    cache = _cache_with_map(tmp_path)
    map_path = tmp_path / "wmap_k_band.npy"

    with patch("polomni.viz.cosmos.helpers.fetch_product", _mock_fetch(map_path)):
        result = run_physics_loop(
            steps=2,
            nside=32,
            map_product_id="wmap_k_band",
            cache=cache,
            seed=0,
        )

    assert isinstance(result, PhysicsLoopResult)
    assert len(result.steps) == 2
    assert len(result.real_axis) == 3
    assert result.real_score >= 0.0
    for step in result.steps:
        assert step.separation_deg >= 0.0
        assert 0.0 <= step.alignment_quality <= 1.0
        assert step.rble_score >= 0.0

    payload = result.to_dict()
    assert payload["map_product_id"] == "wmap_k_band"
    assert payload["nside"] == 32
    assert len(payload["steps"]) == 2
    assert payload["final_separation_deg"] is not None
