"""Tests for real-data pipeline catalog and cache."""

from pathlib import Path

import pytest

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.catalog import (
    CATALOG,
    LITE_PRODUCT_IDS,
    get_product,
    list_products,
)


def test_catalog_has_planck_and_wmap() -> None:
    assert "planck_cmb_tt_power" in CATALOG
    assert "wmap_k_band" in CATALOG
    assert "planck_smica_cmb" in CATALOG


def test_lite_products_are_small_tier() -> None:
    for pid in LITE_PRODUCT_IDS:
        assert get_product(pid).tier == "lite"


def test_list_products_filter() -> None:
    heavy = list_products("heavy")
    assert all(p.tier == "heavy" for p in heavy)
    assert len(heavy) >= 1


def test_cache_manifest_roundtrip(tmp_path: Path) -> None:
    cache = DataCache(tmp_path)
    p = tmp_path / "planck_cmb_tt_power" / "test.txt"
    p.parent.mkdir(parents=True)
    p.write_text("hello")
    cache.record("planck_cmb_tt_power", p, "http://example.com/x.txt")
    entry = cache.get_entry("planck_cmb_tt_power")
    assert entry is not None
    assert cache.resolved_path("planck_cmb_tt_power") == p.resolve()


def test_cache_freshness(tmp_path: Path) -> None:
    cache = DataCache(tmp_path)
    p = tmp_path / "x" / "a.txt"
    p.parent.mkdir(parents=True)
    p.write_text("x")
    cache.record("planck_cmb_tt_power", p, "http://example.com")
    assert cache.is_fresh("planck_cmb_tt_power", max_age_hours=1.0)
    assert not cache.is_fresh("planck_cmb_tt_power", max_age_hours=0.0)
