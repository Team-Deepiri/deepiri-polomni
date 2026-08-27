"""DESI LRG tracer ingest — Guadalupe VAC clustering catalogs (public).

SOTA data path (DESI Data docs / Ross et al. 2025 LSS):
  https://data.desi.lbl.gov/public/dr1/vac/dr1/lss/guadalupe/v1.0/LSScats/clustering/
  LRG_{N,S}_clustering.dat.fits — RA, DEC, Z, WEIGHT (clustering-ready).

Math context (Cai, Zhang, Guan 2025 arXiv:2510.12134):
  SO(2,1) bubble ⇒ only m=0 RDF ℓ=1 + RQF ℓ=2; tomography across Z_e bins
  mitigates ΛCDM variance. ACT×DESI LRG already used for RDF reconstruction.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path
from typing import Any

import numpy as np

from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.sources.dense_tracer import _unique_unit_vectors
from polomni.observatory.pipeline.sources.sky_frames import equatorial_to_galactic

PRODUCT_ID = "desi_lrg_guadalupe"
BASE_URL = (
    "https://data.desi.lbl.gov/public/dr1/vac/dr1/lss/guadalupe/v1.0/"
    "LSScats/clustering"
)
LRG_FILES = (
    "LRG_N_clustering.dat.fits",
    "LRG_S_clustering.dat.fits",
)

# Cai-style electron redshift bins overlapping DESI LRG (z≈0.4–1.1)
DEFAULT_Z_EDGES: tuple[float, ...] = (0.4, 0.6, 0.8, 1.1)
Z_STAR = 0.7  # RDF kernel scale for LRG-depth shells


def desi_cache_dir(cache: DataCache | None = None) -> Path:
    cache = cache or DataCache()
    # Prefer repo-relative data/cache/desi_lrg if present (manual / CLI drop).
    local = Path("data/cache/desi_lrg")
    if local.is_dir():
        return local
    d = cache.root / PRODUCT_ID
    d.mkdir(parents=True, exist_ok=True)
    return d


def fetch_desi_lrg_clustering(
    *,
    cache: DataCache | None = None,
    force: bool = False,
    timeout: float = 300.0,
) -> list[Path]:
    """Download Guadalupe LRG N+S clustering FITS if missing."""
    dest_dir = desi_cache_dir(cache)
    dest_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for name in LRG_FILES:
        dest = dest_dir / name
        if dest.is_file() and not force:
            paths.append(dest)
            continue
        url = f"{BASE_URL}/{name}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            dest.write_bytes(resp.read())
        paths.append(dest)
    return paths


def _radec_to_eq_vecs(ra_deg: np.ndarray, dec_deg: np.ndarray) -> np.ndarray:
    import healpy as hp

    theta = np.radians(90.0 - np.asarray(dec_deg, dtype=float))
    phi = np.radians(np.asarray(ra_deg, dtype=float))
    vecs = np.asarray(hp.ang2vec(theta, phi), dtype=float)
    if vecs.ndim == 1:
        vecs = vecs.reshape(1, 3)
    elif vecs.ndim == 2 and vecs.shape[1] != 3 and vecs.shape[0] == 3:
        vecs = vecs.T
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-15)
    return vecs / norms


def load_desi_lrg_catalog(
    *,
    cache: DataCache | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """Load DESI LRG RA/Dec/z/weight (+ equatorial unit vectors)."""
    from astropy.io import fits

    paths = fetch_desi_lrg_clustering(cache=cache, force=refresh)
    ra_parts: list[np.ndarray] = []
    dec_parts: list[np.ndarray] = []
    z_parts: list[np.ndarray] = []
    w_parts: list[np.ndarray] = []
    for path in paths:
        with fits.open(path) as hdul:
            t = hdul[1].data
            ra_parts.append(np.asarray(t["RA"], dtype=float))
            dec_parts.append(np.asarray(t["DEC"], dtype=float))
            z_parts.append(np.asarray(t["Z"], dtype=float))
            if "WEIGHT" in t.dtype.names:
                w_parts.append(np.asarray(t["WEIGHT"], dtype=float))
            else:
                w_parts.append(np.ones(len(t), dtype=float))
    ra = np.concatenate(ra_parts)
    dec = np.concatenate(dec_parts)
    z = np.concatenate(z_parts)
    weight = np.concatenate(w_parts)
    vecs_eq = _radec_to_eq_vecs(ra, dec)
    return {
        "vecs_eq": vecs_eq,
        "ra": ra,
        "dec": dec,
        "z": z,
        "weight": weight,
        "n_galaxies": int(ra.size),
        "files": [str(p) for p in paths],
        "source": "desi_guadalupe_lrg_clustering",
        "z_range": (float(z.min()), float(z.max())),
    }


def load_desi_lrg_galactic(
    *,
    cache: DataCache | None = None,
    refresh: bool = False,
    with_pscz: bool = False,
) -> dict[str, Any]:
    """Galactic unit vectors for DESI LRG (± optional PSCz stack)."""
    cat = load_desi_lrg_catalog(cache=cache, refresh=refresh)
    gal = equatorial_to_galactic(cat["vecs_eq"])
    sources = ["desi_lrg_guadalupe"]
    counts = {"desi_lrg_guadalupe": int(gal.shape[0])}
    z = cat["z"]
    weight = cat["weight"]
    if with_pscz:
        from polomni.observatory.pipeline.sources.iras_pscz import load_pscz_catalog

        pscz = load_pscz_catalog()
        pgal = equatorial_to_galactic(pscz["vecs_eq"])
        gal = _unique_unit_vectors(np.vstack([gal, pgal]))
        sources.append("iras_pscz")
        counts["iras_pscz"] = int(pscz["vecs_eq"].shape[0])
        # z/weight only meaningful for DESI rows; multi-z uses DESI-only path
    return {
        "vecs_gal": gal,
        "z": z,
        "weight": weight,
        "n_galaxies": int(gal.shape[0]),
        "counts": counts,
        "sources": sources,
        "z_range": cat["z_range"],
        "files": cat["files"],
    }


def desi_z_bins(
    z: np.ndarray,
    vecs_gal: np.ndarray,
    *,
    z_edges: tuple[float, ...] = DEFAULT_Z_EDGES,
) -> list[dict[str, Any]]:
    """Split DESI LRG into Cai-style redshift shells."""
    bins: list[dict[str, Any]] = []
    for z0, z1 in zip(z_edges[:-1], z_edges[1:]):
        m = (z >= z0) & (z < z1)
        n = int(np.sum(m))
        z_mid = 0.5 * (z0 + z1)
        w = float(np.sqrt(max(n, 1)) * z_mid * np.exp(-z_mid / Z_STAR))
        bins.append(
            {
                "z_lo": z0,
                "z_hi": z1,
                "z_mid": z_mid,
                "n_galaxies": n,
                "kernel_weight": w,
                "vecs_gal": vecs_gal[m] if n else vecs_gal[:0],
            }
        )
    return bins
