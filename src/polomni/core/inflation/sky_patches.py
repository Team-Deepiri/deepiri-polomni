"""Map directed diffusion D_eff to HEALPix sky patches (RBLE Eq. 5)."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from polomni.core.geometry import coordinate_to_axis
from polomni.core.inflation.fokker_planck import radon_modified_D_eff
from polomni.core.state.stream_packet import StreamPacket
from polomni.core.superspace.district_graph import DistrictGraph


def map_deff_to_sky_patches(
    packets: list[StreamPacket],
    axes: list[NDArray[np.floating] | list[float]],
    *,
    nside: int = 32,
    h: float = 2.2e-5,
    lambda_coupling: float = 1.0,
) -> np.ndarray:
    """Build a sky map of local D_eff from stream packets at imprint axes.

    Each packet deposits Gaussian-weighted diffusion enhancement near its axis.
    """
    npix = 12 * nside * nside
    deff_map = np.full(npix, h**3 / (8.0 * np.pi**2), dtype=float)

    try:
        import healpy as hp

        theta, phi = hp.pix2ang(nside, np.arange(npix))
        pix_dirs = np.column_stack(
            [np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)]
        )
    except ImportError:
        angles = np.linspace(0, 2 * np.pi, npix, endpoint=False)
        pix_dirs = np.column_stack(
            [np.sin(angles), np.cos(angles), np.zeros(npix)]
        )

    for pkt, axis_in in zip(packets, axes, strict=False):
        axis = coordinate_to_axis(axis_in)
        d_eff = radon_modified_D_eff(h, pkt.phi_array(), lambda_coupling)
        mu = np.abs(pix_dirs @ axis)
        kernel = np.exp(-((1.0 - mu) ** 2) / 0.02)
        deff_map += float(d_eff) * kernel

    return deff_map


def estimate_local_fnl_proxy(deff_map: np.ndarray, *, patch_size: int = 48) -> np.ndarray:
    """Local f_NL proxy ∝ (D_eff - ⟨D_eff⟩) / σ(D_eff) on overlapping sky patches."""
    arr = np.asarray(deff_map, dtype=float).ravel()
    n = arr.size
    if n < patch_size:
        return np.zeros(n, dtype=float)

    mean = float(np.mean(arr))
    std = float(np.std(arr)) + 1e-15
    fnl = (arr - mean) / std

    # Mild spatial smoothing via block average for patch structure.
    if n % patch_size == 0:
        blocks = arr.reshape(-1, patch_size).mean(axis=1)
        block_fnl = (blocks - mean) / std
        fnl = np.repeat(block_fnl, patch_size)[:n]

    return fnl


def deff_fnl_from_simulation(
    graph: DistrictGraph,
    packets: list[StreamPacket],
    *,
    nside: int = 32,
    h: float = 2.2e-5,
) -> dict[str, np.ndarray | list[float]]:
    """Convenience: axes from graph parents → D_eff map + f_NL proxy."""
    axes = []
    for pkt in packets:
        parent = pkt.parent_id if pkt.parent_id is not None else pkt.district_id
        coord = graph.graph.nodes[parent]["coordinate"]
        axes.append(coordinate_to_axis(coord))

    deff = map_deff_to_sky_patches(packets, axes, nside=nside, h=h)
    fnl = estimate_local_fnl_proxy(deff)
    return {
        "deff_map": deff,
        "fnl_proxy": fnl,
        "nside": nside,
        "mean_deff": float(np.mean(deff)),
        "std_deff": float(np.std(deff)),
        "fnl_range": [float(np.min(fnl)), float(np.max(fnl))],
    }
