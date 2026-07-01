"""Equirectangular sky raster for MapLibre globe (real satellite CMB maps)."""

from __future__ import annotations

import io
import time
from typing import Any

import numpy as np

from polomni.viz.cosmos.analytics import sky_payload_cached
from polomni.viz.cosmos.helpers import load_real_sky_map

_RASTER_CACHE: dict[tuple[str, int, int, int], tuple[float, bytes]] = {}
_CACHE_TTL_SEC = 600.0


def _healpix_equirectangular(
    healpix_map: np.ndarray,
    *,
    width: int,
    height: int,
) -> np.ndarray:
    import healpy as hp

    cmap = np.asarray(healpix_map, dtype=float).ravel()
    nside = hp.get_nside(cmap)
    lons = np.linspace(-np.pi, np.pi, width, endpoint=False)
    lats = np.linspace(np.pi / 2, -np.pi / 2, height)
    lon_g, lat_g = np.meshgrid(lons, lats)
    theta = np.pi / 2 - lat_g
    phi = lon_g
    pix = hp.ang2pix(nside, theta.ravel(), phi.ravel())
    return cmap[pix].reshape(height, width)


def _values_to_png(grid: np.ndarray, *, vmin: float, vmax: float) -> bytes:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    norm_grid = np.clip((grid - vmin) / (vmax - vmin + 1e-12), 0.0, 1.0)
    cmap = plt.get_cmap("RdBu_r")
    rgba = (cmap(norm_grid) * 255).astype(np.uint8)
    rgba[..., 3] = 255

    try:
        from PIL import Image

        img = Image.fromarray(rgba, mode="RGBA")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except ImportError:
        fig, ax = plt.subplots(figsize=(grid.shape[1] / 100, grid.shape[0] / 100), dpi=100)
        ax.imshow(grid, origin="upper", cmap="RdBu_r", vmin=vmin, vmax=vmax, aspect="auto")
        ax.axis("off")
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0, transparent=False)
        plt.close(fig)
        return buf.getvalue()


def sky_raster_png(
    *,
    map_product_id: str = "wmap_k_band",
    nside: int = 64,
    width: int = 1024,
    height: int = 512,
    force: bool = False,
) -> bytes:
    """Render a real-sky CMB map as an equirectangular PNG (galactic lon/lat)."""
    width = int(np.clip(width, 256, 4096))
    height = int(np.clip(height, 128, 2048))
    key = (map_product_id, nside, width, height)
    now = time.monotonic()
    if not force and key in _RASTER_CACHE:
        expiry, payload = _RASTER_CACHE[key]
        if now < expiry:
            return payload

    cmb, _, _ = load_real_sky_map(map_product_id=map_product_id, nside=nside)
    grid = _healpix_equirectangular(cmb, width=width, height=height)
    vmin = float(np.percentile(grid, 2))
    vmax = float(np.percentile(grid, 98))
    png = _values_to_png(grid, vmin=vmin, vmax=vmax)
    _RASTER_CACHE[key] = (now + _CACHE_TTL_SEC, png)
    return png


def sky_overlays_geojson(
    *,
    map_product_id: str = "wmap_k_band",
    nside: int = 64,
    force: bool = False,
) -> dict[str, Any]:
    """GeoJSON FeatureCollection for RBLE scar ring and preferred axis."""
    sky = sky_payload_cached(
        map_product_id=map_product_id,
        nside=nside,
        max_pixels=200,
        force=force,
    )
    ring_coords = [
        [lon, lat]
        for lon, lat in zip(sky["scar_ring"]["lon"], sky["scar_ring"]["lat"], strict=True)
    ]
    if ring_coords and ring_coords[0] != ring_coords[-1]:
        ring_coords.append(ring_coords[0])

    features: list[dict[str, Any]] = [
        {
            "type": "Feature",
            "properties": {"kind": "scar_ring", "rble_score": sky["rble_score"]},
            "geometry": {"type": "LineString", "coordinates": ring_coords},
        },
        {
            "type": "Feature",
            "properties": {
                "kind": "preferred_axis",
                "rble_score": sky["rble_score"],
                "null_sigma": sky["null_sigma"],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [sky["axis_marker"]["lon"], sky["axis_marker"]["lat"]],
            },
        },
    ]
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "map_product_id": sky["map_product_id"],
            "nside": sky["nside"],
            "rble_score": sky["rble_score"],
            "null_sigma": sky["null_sigma"],
            "preferred_axis": sky["preferred_axis"],
        },
    }
