"""Tests for Phase E Fisher bubble invariant scanner."""

from __future__ import annotations

import numpy as np

from polomni.observatory.pipeline.sources.bubble_collisions import galactic_edge_mask
from polomni.observatory.pipeline.sources.multiverse_fisher_scan import (
    fisher_scan_report,
    quadratic_fields_mitigated,
    scan_fisher_bubble_axis,
)
from polomni.observatory.pipeline.sources.quadratic_remote_field import (
    axis_separation_deg,
    inject_quadratic_signal,
)
from polomni.observatory.pipeline.sources.rdf_tomography import galaxy_overdensity_map


def _sky(nside: int = 32, seed: int = 0):
    import healpy as hp

    mask = galactic_edge_mask(nside, b_cut=20.0)
    cmb = np.random.default_rng(seed).normal(0, 10.0, hp.nside2npix(nside))
    cmb[~mask] = 0.0
    rng = np.random.default_rng(seed + 1)
    vecs = hp.pix2vec(nside, rng.choice(np.where(mask)[0], size=300, replace=False))
    delta = galaxy_overdensity_map(np.column_stack(vecs), nside, mask)
    return mask, cmb, delta


def test_fisher_scan_recovers_injection() -> None:
    mask, cmb, delta = _sky(seed=3)
    axis = np.array([0.2, 0.1, 0.97])
    axis /= np.linalg.norm(axis)
    t, d = inject_quadratic_signal(cmb, delta, axis, rdf_amp=200.0, rqf_amp=150.0, mask=mask)
    fields = quadratic_fields_mitigated(t, d, mask)
    res = scan_fisher_bubble_axis(fields, mask, nside_dir=8)
    assert res.best_snr > 0.5
    assert res.best_amps.sign_coherent
    assert axis_separation_deg(res.best_axis, axis) < 25.0


def test_fisher_report_injection_gate() -> None:
    mask, cmb, delta = _sky(seed=5)
    axis = np.array([0.05, 0.15, 0.99])
    axis /= np.linalg.norm(axis)
    t, d = inject_quadratic_signal(cmb, delta, axis, rdf_amp=250.0, rqf_amp=180.0, mask=mask)
    rep = fisher_scan_report(t, d, mask, nside_dir=4, n_null=8, seed=0, scar_axis=axis)
    assert rep["observed"]["fisher_snr"] > 0.5
    assert rep["null"]["p_value"] <= 0.5
    assert rep["rble_scar"]["fisher_snr_at_scar"] > 0.3
