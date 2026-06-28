"""Tests for expanded data catalog products."""

from polomni.observatory.pipeline.catalog import CATALOG, get_product, gwosc_event_detail_url


def test_catalog_new_lite_products() -> None:
    assert "planck_int_mask" in CATALOG
    assert "wmap_tt_power" in CATALOG
    assert "camb_lcdm_cl" in CATALOG
    assert "sdss_bao_ladder" in CATALOG
    assert get_product("wmap_tt_power").tier == "lite"
    assert get_product("sdss_bao_ladder").kind == "json"


def test_gwosc_event_detail_url() -> None:
    url = gwosc_event_detail_url("GW150914")
    assert url == "https://gwosc.org/api/v2/events/GW150914"
