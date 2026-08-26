"""Tests for Phase F multi-z Fisher tomography."""

from __future__ import annotations

import numpy as np

from polomni.observatory.pipeline.sources.bubble_collisions import galactic_edge_mask
from polomni.observatory.pipeline.sources.multi_z_tomography import (
    assign_z_bins,
    mean_pairwise_axis_sep_deg,
    multi_z_fisher_report,
    redshift_kernel_weight,
    stack_fisher_vector,
    ZBinFisherResult,
)
from polomni.observatory.pipeline.sources.quadratic_remote_field import (
    axis_separation_deg,
    inject_quadratic_signal,
)
from polomni.observatory.pipeline.sources.rdf_tomography import galaxy_overdensity_map


def test_redshift_kernel_and_bins() -> None:
    assert redshift_kernel_weight(0.02, 1000) > redshift_kernel_weight(0.001, 1000)
    z = np.array([0.005, 0.02, 0.05, 0.2, np.nan])
    masks = assign_z_bins(z, (0.0, 0.01, 0.04, 0.15))
    assert int(masks[0].sum()) == 1
    assert int(masks[1].sum()) == 1
    assert int(masks[2].sum()) == 1


def test_stack_prefers_coherent_axes() -> None:
    axis = np.array([0.1, 0.2, 0.97])
    axis /= np.linalg.norm(axis)
    bins = [
        ZBinFisherResult(0, 0.01, 0.005, 200, 1.0, axis, 0.9, True, 0.8, 0.7),
        ZBinFisherResult(0.01, 0.04, 0.025, 300, 2.0, axis, 0.85, True, 0.75, 0.65),
    ]
    snr, stacked, ok = stack_fisher_vector(bins)
    assert ok
    assert snr > 0.7
    assert axis_separation_deg(stacked, axis) < 1.0
    assert mean_pairwise_axis_sep_deg([axis, axis]) < 1.0


def test_multi_z_recovers_injection() -> None:
    import healpy as hp

    nside = 32
    mask = galactic_edge_mask(nside, b_cut=20.0)
    rng = np.random.default_rng(7)
    cmb = rng.normal(0, 5.0, hp.nside2npix(nside))
    cmb[~mask] = 0.0
    axis = np.array([0.15, 0.05, 0.987])
    axis /= np.linalg.norm(axis)
    # Plant galaxies with a shared dipole bias so every z-shell sees the same axis
    pix = np.where(mask)[0]
    dirs = np.column_stack(hp.pix2vec(nside, pix))
    mu = dirs @ axis
    # Prefer pixels aligned with the bubble axis
    w = np.clip(mu, 0, None) ** 2 + 0.05
    w /= w.sum()
    chosen = rng.choice(pix, size=900, replace=True, p=w)
    vecs = np.column_stack(hp.pix2vec(nside, chosen))
    z = np.concatenate(
        [
            rng.uniform(0.001, 0.011, 300),
            rng.uniform(0.013, 0.034, 300),
            rng.uniform(0.036, 0.10, 300),
        ]
    )
    delta = galaxy_overdensity_map(vecs, nside, mask)
    t, _ = inject_quadratic_signal(
        cmb, delta, axis, rdf_amp=250.0, rqf_amp=180.0, delta_couple=0.4, mask=mask
    )
    # Re-inject tracer coupling into the sky map is lost on rebuild — boost CMB only
    # and rely on shared galaxy dipole bias across shells for axis coherence.
    rep = multi_z_fisher_report(
        t, vecs, z, mask, nside_dir=4, n_null=4, seed=0, scar_axis=axis
    )
    assert rep["n_bins_used"] >= 2
    assert rep["stacked"]["fisher_snr"] > 0.25
    # Scar-channel SNR must respond at the planted axis
    assert float(rep["rble_scar"]["fisher_snr_at_scar"]) > 0.15
    assert axis_separation_deg(np.asarray(rep["stacked"]["axis_gal"]), axis) < 50.0
