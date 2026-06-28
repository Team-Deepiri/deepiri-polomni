"""Mollweide projection for HEALPix CMB maps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _unit_vector_to_lonlat(n_hat: np.ndarray) -> tuple[float, float]:
    n = np.asarray(n_hat, dtype=float).ravel()
    norm = np.linalg.norm(n)
    if norm < 1e-15:
        raise ValueError("highlight_axis must be a non-zero 3-vector")
    n = n / norm
    lat = float(np.arcsin(np.clip(n[2], -1.0, 1.0)))
    lon = float(np.arctan2(n[1], n[0]))
    return lon, lat


def _draw_axis_highlight(n_hat: np.ndarray) -> None:
    lon, lat = _unit_vector_to_lonlat(n_hat)
    try:
        import healpy as hp

        hp.projscatter(
            np.degrees(lon),
            np.degrees(lat),
            marker="x",
            s=120,
            c="gold",
            linewidths=2,
        )
    except ImportError:
        ax = plt.gca()
        ax.plot(lon, lat, marker="x", markersize=12, color="gold", markeredgewidth=2)


def plot_mollweide(
    healpix_map: np.ndarray,
    *,
    title: str = "CMB Map",
    cmap: str = "RdBu_r",
    ax: Any | None = None,
    show: bool = False,
    save_path: str | Path | None = None,
    highlight_axis: np.ndarray | None = None,
) -> Any:
    """Plot a HEALPix map in Mollweide projection.

    Uses ``healpy.mollview`` when available; otherwise a coarse pixel scatter.

    Parameters
    ----------
    healpix_map:
        1-D HEALPix temperature map.
    title:
        Plot title.
    cmap:
        Matplotlib colormap name.
    ax:
        Optional matplotlib axes (healpy creates its own figure if None).
    show:
        Call ``plt.show()`` when True.
    save_path:
        When set, save the figure to this path (PNG recommended).
    highlight_axis:
        Optional unit 3-vector ``[x, y, z]`` to mark on the map.

    Returns
    -------
    matplotlib figure or axes handle.
    """
    healpix_map = np.asarray(healpix_map, dtype=float).ravel()
    fig: Any

    try:
        import healpy as hp

        hp.mollview(
            healpix_map,
            title=title,
            cmap=plt.get_cmap(cmap),
            hold=True,
        )
        fig = plt.gcf()
    except ImportError:
        if ax is None:
            fig, ax = plt.subplots(subplot_kw={"projection": "mollweide"})
        else:
            fig = ax.figure
        n = healpix_map.size
        lon = np.linspace(-np.pi, np.pi, n)
        lat = np.linspace(-np.pi / 2, np.pi / 2, n)
        lon_grid, lat_grid = np.meshgrid(lon, lat)
        sc = ax.scatter(
            lon_grid.ravel(),
            lat_grid.ravel(),
            c=np.tile(healpix_map, n // healpix_map.size + 1)[: lon_grid.size],
            s=1,
            cmap=cmap,
        )
        ax.set_title(title)
        plt.colorbar(sc, ax=ax, shrink=0.6)

    if highlight_axis is not None:
        _draw_axis_highlight(highlight_axis)

    if save_path is not None:
        out = Path(save_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        if not show:
            plt.close(fig)

    if show:
        plt.show()
    return fig if ax is None else ax
