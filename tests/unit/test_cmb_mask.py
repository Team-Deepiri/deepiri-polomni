"""Tests for clean-sky CMB mask helpers."""

from __future__ import annotations

import numpy as np

from polomni.observatory.pipeline.sources.cmb_mask import (
    apply_clean_sky_mask,
    galactic_latitude_cut,
)


def test_galactic_latitude_cut_keeps_poles() -> None:
    # +z is Galactic north pole → b=+90
    poles = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, -1.0], [1.0, 0.0, 0.0]])
    keep = galactic_latitude_cut(poles, b_cut_deg=20.0)
    assert keep[0] and keep[1]
    # Equatorial galactic (x) has b≈0 → cut
    assert not keep[2]


def test_apply_clean_sky_mask_fsky() -> None:
    import healpy as hp

    nside = 8
    cmb = np.ones(hp.nside2npix(nside))
    masked, meta = apply_clean_sky_mask(cmb, nside=nside, b_cut_deg=20.0, fill="mean")
    assert 0.4 < meta["f_sky"] < 0.9
    assert masked.shape == cmb.shape
    assert meta["planck_int_mask"] in (True, False)
