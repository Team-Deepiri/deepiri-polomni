"""Mollweide projection for HEALPix CMB maps."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np


def plot_mollweide(
    healpix_map: np.ndarray,
    *,
    title: str = "CMB Map",
    cmap: str = "RdBu_r",
    ax: Any | None = None,
    show: bool = False,
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

    Returns
    -------
    matplotlib axes or healpy figure handle.
    """
    healpix_map = np.asarray(healpix_map, dtype=float).ravel()

    try:
        import healpy as hp

        hp.mollview(
            healpix_map,
            title=title,
            cmap=plt.get_cmap(cmap),
            hold=True,
        )
        fig = plt.gcf()
        if show:
            plt.show()
        return fig
    except ImportError:
        if ax is None:
            _, ax = plt.subplots(subplot_kw={"projection": "mollweide"})
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
        if show:
            plt.show()
        return ax
