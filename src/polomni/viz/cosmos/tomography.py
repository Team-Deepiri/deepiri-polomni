"""Radon tomography visualization payloads — novel S² landscape + geodesic slices."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np

from polomni.observatory.scoring.hierarchical_search import hierarchical_sky_search
from polomni.observatory.scoring.radon_tomography import (
    build_radon_tomogram,
    fingerprint_bifurcation_peaks,
    rble_axis_landscape,
)
from polomni.viz.cosmos.helpers import load_iqu_maps, load_real_sky_map


def cosmos_tomogram_payload(
    *,
    map_product_id: str = "wmap_k_band",
    nside: int = 64,
    n_eta: int = 128,
) -> dict[str, Any]:
    """Geodesic Radon tomogram R(η), bifurcation |R''|, optional TE conductance M(η)."""
    t_map, q_map, u_map, pid, _ = load_iqu_maps(map_product_id=map_product_id, nside=nside)
    detection = hierarchical_sky_search(t_map, coarse_nside=min(16, nside // 4 or 16), seed=0)
    axis = np.asarray(detection.preferred_axis, dtype=float)

    tomogram = build_radon_tomogram(
        t_map,
        axis,
        n_eta=n_eta,
        q_map=q_map,
        u_map=u_map,
        method="transform",
    )
    peaks = fingerprint_bifurcation_peaks(tomogram.bifurcation, tomogram.eta)

    return {
        "map_product_id": pid,
        "nside": nside,
        "detection": detection.model_dump(mode="json"),
        "tomogram": tomogram.to_dict(),
        "fingerprint": peaks,
        "equation": "S_RBLE(n̂) = ∫₀²π |R_S²[T⊗W_string](n̂,η)| dη",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def cosmos_landscape_payload(
    *,
    map_product_id: str = "wmap_k_band",
    nside: int = 64,
    nside_dirs: int = 8,
) -> dict[str, Any]:
    """RBLE axis landscape — S_RBLE over all HEALPix directions (novel scar field on S²)."""
    t_map, _, _, pid, _ = load_iqu_maps(map_product_id=map_product_id, nside=nside)
    landscape = rble_axis_landscape(t_map, nside_dirs=nside_dirs, n_eta=24)
    landscape["map_product_id"] = pid
    landscape["timestamp"] = datetime.now(timezone.utc).isoformat()
    return landscape
