"""Tests for P1 study runner (synthetic / no network)."""

import json
from pathlib import Path

import numpy as np
import pytest

from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.cache import CacheEntry, CacheManifest
from polomni.observatory.studies.p1_runner import run_p1_study


@pytest.fixture
def study_cache(tmp_path) -> DataCache:
    cache = DataCache(tmp_path)
    nside = 128
    # Minimal fake FITS path for study runner
    product_dir = tmp_path / "wmap_k_band"
    product_dir.mkdir()
    # Use healpy to write fits if available, else skip
    map_path = product_dir / "test_map.fits"
    try:
        import healpy as hp

        m = synthetic_cmb_map(128, seed=1)
        hp.write_map(map_path, m, overwrite=True)
    except ImportError:
        pytest.skip("healpy required for p1_runner test")

    manifest = CacheManifest(
        entries={
            "wmap_k_band": CacheEntry(
                product_id="wmap_k_band",
                path=str(map_path),
                url="test://local",
                fetched_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
                size_bytes=map_path.stat().st_size,
            )
        }
    )
    cache.save_manifest(manifest)
    return cache


def test_p1_runner_writes_result(study_cache, tmp_path) -> None:
    config = Path("data/studies/p1_holdout/study_config.json")
    out = tmp_path / "RESULT.json"
    result = run_p1_study(
        config,
        cache=study_cache,
        calibration=True,
        output_path=out,
    )
    assert out.is_file()
    assert result["study_id"] == "p1_cmb_radon_scar"
    assert "detection" in result
    assert "null_tier_comparison" in result
    assert json.loads(out.read_text(encoding="utf-8")) == result
