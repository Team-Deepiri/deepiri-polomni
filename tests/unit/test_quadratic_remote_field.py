"""Tests for MV quadratic RDF/RQF estimator and Cai template matching."""

from __future__ import annotations

import numpy as np

from polomni.observatory.pipeline.sources.bubble_collisions import galactic_edge_mask
from polomni.observatory.pipeline.sources.cai_bubble_template import (
    match_cai_bubble_template,
    search_cai_template_axis,
)
from polomni.observatory.pipeline.sources.quadratic_remote_field import (
    axis_separation_deg,
    inject_quadratic_signal,
    quadratic_remote_fields,
)


def _sky(nside: int = 32, seed: int = 0):
    import healpy as hp

    mask = galactic_edge_mask(nside, b_cut=20.0)
    cmb = np.random.default_rng(seed).normal(0, 10.0, hp.nside2npix(nside))
    cmb[~mask] = 0.0
    rng = np.random.default_rng(seed + 1)
    vecs = hp.pix2vec(nside, rng.choice(np.where(mask)[0], size=300, replace=False))
    from polomni.observatory.pipeline.sources.rdf_tomography import galaxy_overdensity_map

    delta = galaxy_overdensity_map(np.column_stack(vecs), nside, mask)
    return mask, cmb, delta


def test_quadratic_recovers_injected_axis() -> None:
    mask, cmb, delta = _sky()
    axis = np.array([0.15, -0.2, 0.97])
    axis /= np.linalg.norm(axis)
    t, d = inject_quadratic_signal(cmb, delta, axis, rdf_amp=120.0, rqf_amp=90.0, mask=mask)
    fields = quadratic_remote_fields(t, d, mask)
    assert axis_separation_deg(fields.dipole_axis, axis) < 25.0
    assert fields.axis_separation_deg < 20.0


def test_cai_template_match_injection() -> None:
    mask, cmb, delta = _sky(seed=2)
    axis = np.array([0.1, 0.3, 0.95])
    axis /= np.linalg.norm(axis)
    t, d = inject_quadratic_signal(cmb, delta, axis, rdf_amp=150.0, rqf_amp=100.0, mask=mask)
    fields = quadratic_remote_fields(t, d, mask)
    best_axis, best, _ = search_cai_template_axis(fields, mask, nside_dir=16)
    assert axis_separation_deg(best_axis, axis) < 25.0
    assert best["combined_correlation"] > 0.3
    at_axis = match_cai_bubble_template(fields, mask, axis=axis)
    assert at_axis["combined_correlation"] > 0.25
