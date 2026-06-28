"""Shared HEALPix sky loading helpers for cosmos viz."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from polomni.observatory.ingest.healpix_loader import downsample_map, load_healpix_map
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.catalog import get_product
from polomni.observatory.pipeline.downloader import fetch_product


def axis_lonlat(axis: list[float] | np.ndarray) -> tuple[float, float]:
    import healpy as hp

    a = np.asarray(axis, dtype=float)
    a = a / (np.linalg.norm(a) + 1e-15)
    theta, phi = hp.vec2ang(a)
    lat = float(90.0 - np.degrees(theta)[0])
    lon = float(np.degrees(phi)[0])
    return lon, lat


def great_circle_ring(axis: np.ndarray, n_pts: int = 72) -> tuple[list[float], list[float]]:
    import healpy as hp

    axis = np.asarray(axis, dtype=float)
    axis = axis / (np.linalg.norm(axis) + 1e-15)
    tangent = np.cross(axis, np.array([0.0, 0.0, 1.0]))
    if np.linalg.norm(tangent) < 1e-8:
        tangent = np.cross(axis, np.array([0.0, 1.0, 0.0]))
    tangent /= np.linalg.norm(tangent) + 1e-15
    bitangent = np.cross(axis, tangent)
    lons: list[float] = []
    lats: list[float] = []
    for eta in np.linspace(0, 2 * np.pi, n_pts, endpoint=False):
        pt = np.cos(eta) * tangent + np.sin(eta) * bitangent
        pt /= np.linalg.norm(pt)
        theta, phi = hp.vec2ang(pt)
        lats.append(float(90.0 - np.degrees(theta)[0]))
        lons.append(float(np.degrees(phi)[0]))
    return lons, lats


def load_real_sky_map(
    *,
    map_product_id: str = "wmap_k_band",
    nside: int = 64,
    cache: DataCache | None = None,
) -> tuple[np.ndarray, str, Path | None]:
    cache = cache or DataCache()
    path = cache.resolved_path(map_product_id)
    if path is None:
        product = get_product(map_product_id)
        fetch = fetch_product(product, cache, force=False)
        path = fetch.path
    raw = load_healpix_map(path, field="T")
    cmb = downsample_map(raw, nside)
    return cmb, map_product_id, path


def load_iqu_maps(
    *,
    map_product_id: str = "planck_smica_cmb",
    nside: int = 64,
    cache: DataCache | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, str, Path | None]:
    """Load T and polarization Q/U; derive Q/U proxy from T when absent."""
    from polomni.observatory.ingest.polarization import extract_qu_maps

    cache = cache or DataCache()
    path = cache.resolved_path(map_product_id)
    if path is None:
        product = get_product(map_product_id)
        fetch = fetch_product(product, cache, force=False)
        path = fetch.path
    try:
        t_raw = load_healpix_map(path, field="T")
        q_raw = load_healpix_map(path, field="Q")
        u_raw = load_healpix_map(path, field="U")
    except (ValueError, IndexError, KeyError):
        t_raw = load_healpix_map(path, field="I")
        t_down = downsample_map(t_raw, nside)
        q_down, u_down = extract_qu_maps(t_down)
        return t_down, q_down, u_down, map_product_id, path

    t_map = downsample_map(t_raw, nside)
    q_map = downsample_map(q_raw, nside)
    u_map = downsample_map(u_raw, nside)
    return t_map, q_map, u_map, map_product_id, path
