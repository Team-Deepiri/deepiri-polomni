"""Integration tests hitting real public cosmology endpoints (lite products only)."""

import pytest

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.catalog import get_product
from polomni.observatory.pipeline.downloader import fetch_product
from polomni.observatory.pipeline.sources.cosmology import load_planck_tt_power
from polomni.observatory.pipeline.sources.gwosc import fetch_gwtc_events


@pytest.mark.integration
@pytest.mark.observatory
def test_fetch_planck_power_spectrum_live(tmp_path) -> None:
    cache = DataCache(tmp_path)
    product = get_product("planck_cmb_tt_power")
    result = fetch_product(product, cache, force=True)
    assert result.path.exists()
    assert result.bytes_written > 1000
    ps = load_planck_tt_power(result.path)
    assert ps.ell.min() > 0
    assert ps.dl.max() > 1000


@pytest.mark.integration
@pytest.mark.observatory
def test_fetch_gwosc_catalog_live(tmp_path) -> None:
    cache = DataCache(tmp_path)
    snap = fetch_gwtc_events(cache, max_pages=1)
    assert snap.results_count >= 20
    assert snap.events[0].name.startswith("GW")

@pytest.mark.integration
@pytest.mark.observatory
def test_fetch_wmap_k_band_live(tmp_path) -> None:
    cache = DataCache(tmp_path)
    product = get_product("wmap_k_band")
    result = fetch_product(product, cache, force=True)
    assert result.path.exists()
    assert result.bytes_written > 1000