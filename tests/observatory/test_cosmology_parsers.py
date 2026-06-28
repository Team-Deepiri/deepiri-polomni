"""Tests for cosmology text product parsers."""

from pathlib import Path

import pytest

from polomni.observatory.pipeline.sources.cosmology import (
    load_planck_cosmo_params,
    load_planck_tt_power,
)

SAMPLE_POWER = """# l Dl -dDl +dDl BestFit
47.7112240 1479.33552 50.7654876 50.7654876 1461.11304
76.4716065 2034.96833 54.7101576 54.7101576 2062.38073
"""

SAMPLE_COSMO = """# comment
H0 = 67.36
omegal = 0.6847
"""


def test_load_planck_tt_power(tmp_path: Path) -> None:
    f = tmp_path / "cl.txt"
    f.write_text(SAMPLE_POWER)
    ps = load_planck_tt_power(f)
    assert ps.ell.shape == (2,)
    assert ps.dl[0] == pytest.approx(1479.33552)


def test_load_planck_cosmo_params(tmp_path: Path) -> None:
    f = tmp_path / "cosmo.txt"
    f.write_text(SAMPLE_COSMO)
    cp = load_planck_cosmo_params(f)
    assert cp.params["H0"] == pytest.approx(67.36)
    assert cp.params["omegal"] == pytest.approx(0.6847)
