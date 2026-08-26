"""Tests for Phase H dense LRG Fisher helpers (no network required)."""

from __future__ import annotations

import numpy as np

from polomni.observatory.pipeline.sources.dense_tracer import forecast_fisher_snr
from polomni.observatory.pipeline.sources.dense_lrg_fisher import PRODUCT_ID


def test_product_id() -> None:
    assert PRODUCT_ID == "sdss_lrg_dense"


def test_dense_vs_pscz_scaling_expectation() -> None:
    # If SNR scales as √N, doubling N → √2 SNR
    f = forecast_fisher_snr(1.0, n_gal_now=1e4, n_gal_future=2e4, f_sky_now=0.5, f_sky_future=0.5)
    assert abs(f["scale_factor"] - np.sqrt(2.0)) < 1e-3
    assert abs(f["snr_forecast"] - np.sqrt(2.0)) < 1e-3
