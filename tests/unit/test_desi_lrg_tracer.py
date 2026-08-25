"""Unit tests for DESI LRG tracer helpers (no network if FITS cached)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from polomni.observatory.pipeline.sources.desi_lrg_tracer import (
    desi_z_bins,
    _radec_to_eq_vecs,
)


def test_radec_to_eq_vecs_shape() -> None:
    ra = np.array([0.0, 90.0, 180.0])
    dec = np.array([0.0, 0.0, 45.0])
    v = _radec_to_eq_vecs(ra, dec)
    assert v.shape == (3, 3)
    norms = np.linalg.norm(v, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-6)


def test_desi_z_bins_partition() -> None:
    rng = np.random.default_rng(0)
    n = 1000
    z = rng.uniform(0.4, 1.1, size=n)
    vecs = rng.normal(size=(n, 3))
    vecs /= np.linalg.norm(vecs, axis=1)[:, None]
    bins = desi_z_bins(z, vecs)
    assert len(bins) == 3
    assert sum(b["n_galaxies"] for b in bins) == n


def test_cached_desi_fits_loads_if_present() -> None:
    root = Path("data/cache/desi_lrg")
    if not (root / "LRG_N_clustering.dat.fits").is_file():
        return
    from polomni.observatory.pipeline.sources.desi_lrg_tracer import load_desi_lrg_catalog

    cat = load_desi_lrg_catalog(refresh=False)
    assert cat["n_galaxies"] > 100_000
    assert cat["z_range"][0] >= 0.39
