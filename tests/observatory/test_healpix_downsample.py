"""Tests for HEALPix downsample utilities."""

import numpy as np
import pytest

from polomni.observatory.ingest.healpix_loader import downsample_map, map_nside


def test_map_nside_roundtrip() -> None:
    nside = 64
    npix = 12 * nside * nside
    assert map_nside(np.zeros(npix)) == nside


def test_downsample_identity() -> None:
    nside = 32
    m = np.random.default_rng(0).standard_normal(12 * nside * nside)
    out = downsample_map(m, nside)
    assert out.shape == m.shape


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("healpy") is None,
    reason="healpy required",
)
def test_downsample_healpy() -> None:
    import healpy as hp

    nside_in = 64
    m = hp.synfast([0, 0, 1.0] + [0] * 510, nside_in, new=True)
    out = downsample_map(m, 16)
    assert map_nside(out) == 16
