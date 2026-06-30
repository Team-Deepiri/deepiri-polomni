"""CMB imprinting from district simulation stream packets (RBLE loop)."""

from __future__ import annotations

import numpy as np

from polomni.core.geometry import coordinate_to_axis
from polomni.core.state.stream_packet import StreamPacket
from polomni.core.superspace.district_graph import DistrictGraph
from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.scoring.rble_signature import inject_synthetic_scar


def imprint_axis_from_graph(graph: DistrictGraph, district_id: int) -> np.ndarray:
    """Preferred scar axis from a district node's coordinate."""
    if district_id not in graph.graph:
        raise KeyError(f"district {district_id} not in graph")
    coord = graph.graph.nodes[district_id]["coordinate"]
    return coordinate_to_axis(coord)


def imprint_cmb_from_packets(
    packets: list[StreamPacket],
    graph: DistrictGraph,
    *,
    nside: int = 64,
    seed: int | None = 0,
    base_amplitude: float = 6.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Build a CMB map scarred along each packet's parent stream axis."""
    cmb = synthetic_cmb_map(nside, seed=seed)
    if not packets:
        return cmb, np.array([0.0, 0.0, 1.0])

    axes: list[np.ndarray] = []
    weights: list[float] = []
    for pkt in packets:
        parent_id = pkt.parent_id if pkt.parent_id is not None else pkt.district_id
        axis = imprint_axis_from_graph(graph, parent_id)
        flux = float(np.sum(np.abs(pkt.phi_array())))
        amp = base_amplitude * flux * (1.0 + 0.01 * pkt.information_trace)
        cmb = inject_synthetic_scar(cmb, axis, amplitude=amp)
        axes.append(axis)
        weights.append(flux)

    w = np.asarray(weights, dtype=float)
    w = w / (w.sum() + 1e-15)
    true_axis = np.sum(np.stack(axes) * w[:, None], axis=0)
    true_axis = true_axis / (np.linalg.norm(true_axis) + 1e-15)
    return cmb, true_axis
