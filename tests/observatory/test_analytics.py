"""Tests for pipeline analytics."""

from pathlib import Path

import numpy as np
import pytest

from polomni.observatory.pipeline.analytics import plot_cached_power_spectrum
from polomni.observatory.pipeline.sources.cosmology import load_planck_tt_power
from polomni.viz.power_spectrum import plot_power_spectrum


SAMPLE_POWER = """47.7112240 1479.33552 50.7654876 50.7654876 1461.11304
76.4716065 2034.96833 54.7101576 54.7101576 2062.38073
"""


def test_plot_power_spectrum(tmp_path: Path) -> None:
    f = tmp_path / "cl.txt"
    f.write_text(SAMPLE_POWER)
    ps = load_planck_tt_power(f)
    out = plot_power_spectrum(ps.ell, ps.dl, save_path=tmp_path / "ps.png")
    assert out.exists()
    assert out.stat().st_size > 100


def test_plot_cached_power_spectrum_missing_raises(tmp_path: Path) -> None:
    from polomni.observatory.pipeline.cache import DataCache

    cache = DataCache(root=tmp_path / "cache")
    with pytest.raises(FileNotFoundError):
        plot_cached_power_spectrum(cache, product_id="planck_cmb_tt_power", output_path=tmp_path / "x.png")
