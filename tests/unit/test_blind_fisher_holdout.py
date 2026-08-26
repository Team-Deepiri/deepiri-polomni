"""Tests for Phase G blind Fisher holdout + dense tracer forecast."""

from __future__ import annotations

import numpy as np

from polomni.observatory.pipeline.sources.blind_fisher_holdout import fisher_snr_at_axis
from polomni.observatory.pipeline.sources.bubble_collisions import galactic_edge_mask
from polomni.observatory.pipeline.sources.dense_tracer import forecast_fisher_snr
from polomni.observatory.pipeline.sources.quadratic_remote_field import inject_quadratic_signal
from polomni.observatory.pipeline.sources.rdf_tomography import galaxy_overdensity_map


def test_forecast_scales_with_n_gal() -> None:
    f = forecast_fisher_snr(1.0, n_gal_now=1e4, n_gal_future=1e6, f_sky_now=0.5, f_sky_future=0.5)
    assert f["scale_factor"] == 10.0
    assert f["snr_forecast"] == 10.0
    assert f["passes_snr_2_forecast"] is True


def test_fisher_snr_at_axis_recovers_injection() -> None:
    import healpy as hp

    nside = 32
    mask = galactic_edge_mask(nside, b_cut=20.0)
    rng = np.random.default_rng(11)
    cmb = rng.normal(0, 10.0, hp.nside2npix(nside))
    cmb[~mask] = 0.0
    axis = np.array([0.1, 0.2, 0.97])
    axis /= np.linalg.norm(axis)
    pix = rng.choice(np.where(mask)[0], size=400, replace=False)
    vecs = np.column_stack(hp.pix2vec(nside, pix))
    delta = galaxy_overdensity_map(vecs, nside, mask)
    t, d = inject_quadratic_signal(cmb, delta, axis, rdf_amp=200.0, rqf_amp=150.0, mask=mask)
    snr_true = fisher_snr_at_axis(t, d, mask, axis)
    snr_wrong = fisher_snr_at_axis(t, d, mask, np.array([1.0, 0.0, 0.0]))
    assert snr_true > 0.4
    assert snr_true > snr_wrong
