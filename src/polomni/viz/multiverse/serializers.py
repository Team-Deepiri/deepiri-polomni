"""Multiverse visualization data serializers for the React frontend."""

from __future__ import annotations

from typing import Any

import numpy as np

from polomni.core.conservation import compute_information_trace
from polomni.core.gravity.information_tensor import information_tensor_N
from polomni.core.landscape.kahler import kahler_total
from polomni.core.landscape.superpotential import superpotential_W
from polomni.core.radon.vacuum_stream import RadonVacuumPipeline
from polomni.core.superspace.district_graph import ChoicePolicy, DistrictGraph
from polomni.integration.closed_loop import run_closed_loop
from polomni.integration.cmb_imprint import imprint_cmb_from_packets
from polomni.math.proofs.base import load_cached_suite, prove_all
from polomni.observatory.ingest.healpix_loader import downsample_map, load_healpix_map, synthetic_cmb_map
from polomni.observatory.reports.comparison import latest_report, load_report
from polomni.observatory.scoring.rble_signature import compute_rble_signature


def district_graph_3d(
    *,
    choices: int = 5,
    districts: int = 1,
    steps: int = 2,
    policy: str = "uniform",
) -> dict[str, Any]:
    graph = DistrictGraph()
    roots = []
    for i in range(districts):
        roots.append(
            graph.add_district(
                mass=1.0 + 0.1 * i,
                law_of_gravity=[6.674e-11, 1.1e-52],
                coordinate=[float(i), 0.0, 0.0],
                lambda_vacuum=1.0e-52,
            )
        )
    choice_policy = ChoicePolicy(policy)
    for root in roots:
        graph.run_simulation_chain(
            steps=steps,
            num_choices=choices,
            policy=choice_policy,
        )

    return _graph_to_viz_payload(graph)


def _graph_to_viz_payload(graph: DistrictGraph) -> dict[str, Any]:
    nodes = []
    for nid, attrs in graph.graph.nodes(data=True):
        coord = attrs.get("coordinate", [0, 0, 0])
        nodes.append(
            {
                "id": str(nid),
                "mass": float(attrs.get("mass", 1.0)),
                "x": float(coord[0]) if len(coord) > 0 else 0.0,
                "y": float(coord[1]) if len(coord) > 1 else 0.0,
                "z": float(coord[2]) if len(coord) > 2 else 0.0,
            }
        )
    edges = []
    for u, v, data in graph.graph.edges(data=True):
        edges.append(
            {
                "source": str(u),
                "target": str(v),
                "conductance": float(data.get("conductance", 0.0)),
            }
        )
    return {"nodes": nodes, "edges": edges}


def closed_loop_panel(
    *,
    steps: int = 3,
    num_choices: int = 4,
    nside: int = 32,
    policy: str = "axis_biased",
    seed: int = 0,
) -> dict[str, Any]:
    """Closed-loop viz: sim imprint → RBLE scan → feedback history."""
    graph, results = run_closed_loop(
        steps=steps,
        num_choices=num_choices,
        nside=nside,
        seed=seed,
        policy=ChoicePolicy(policy),
    )
    last = results[-1] if results else None
    cmb = None
    if last is not None:
        packets = graph.run_simulation_chain(steps=1, num_choices=num_choices)
        cmb, _ = imprint_cmb_from_packets(packets, graph, nside=nside, seed=seed)

    return {
        "steps": [r.to_dict() for r in results],
        "graph": _graph_to_viz_payload(graph),
        "final_axis_error_deg": last.axis_error_deg if last else None,
        "cmb_values": cmb.tolist() if cmb is not None else [],
        "nside": nside,
    }


def landscape_surface(*, grid_size: int = 32) -> dict[str, Any]:
    re = np.linspace(0.5, 2.0, grid_size)
    im = np.linspace(-1.0, 1.0, grid_size)
    x, y = np.meshgrid(re, im)
    z = np.zeros_like(x)
    for i in range(grid_size):
        for j in range(grid_size):
            t = complex(x[i, j], y[i, j])
            z[i, j] = kahler_total(t, i_trace=0.3, phi_stream_flux=0.1)
    return {
        "x": x.tolist(),
        "y": y.tolist(),
        "z": z.tolist(),
        "title": "Kahler K_total(T, T̄)",
    }


def scar_sphere(
    *,
    synthetic: bool = True,
    nside: int = 32,
    map_product_id: str = "wmap_k_band",
) -> dict[str, Any]:
    if synthetic:
        cmb = synthetic_cmb_map(nside, seed=0)
    else:
        from polomni.observatory.pipeline.cache import DataCache
        from polomni.observatory.pipeline.catalog import get_product
        from polomni.observatory.pipeline.downloader import fetch_product

        cache = DataCache()
        product = get_product(map_product_id)
        path = fetch_product(product, cache).path
        raw = load_healpix_map(path, field="T")
        cmb = downsample_map(raw, nside)

    report = compute_rble_signature(cmb)
    try:
        import healpy as hp

        theta, phi = hp.pix2ang(nside, np.arange(cmb.size))
        lon = np.degrees(phi)
        lat = 90.0 - np.degrees(theta)
    except ImportError:
        n_pix = cmb.size
        lat = np.linspace(-90, 90, n_pix)
        lon = np.linspace(-180, 180, n_pix)

    return {
        "lat": lat.tolist() if hasattr(lat, "tolist") else list(lat),
        "lon": lon.tolist() if hasattr(lon, "tolist") else list(lon),
        "values": cmb.tolist(),
        "preferred_axis": report.preferred_axis,
        "rble_score": report.rble_score,
        "nside": nside,
    }


def stream_flux_series(*, packets: int = 5) -> dict[str, Any]:
    pipeline = RadonVacuumPipeline(num_choices=packets)
    psi = np.random.randn(16, 16, 16) * 0.01
    psi[8, 8, 8] = 1.0
    bubble = pipeline.encapsulate_and_scan(psi)
    rotated = pipeline.rotate_particle_properties(bubble)
    packet = pipeline.stream_to_vacuum(rotated)
    stages = [
        {"stage": "radon_scan", "flux": float(np.sum(np.abs(bubble))), "trace": 0.0},
        {"stage": "so3_rotate", "flux": float(np.sum(np.abs(rotated))), "trace": 0.0},
        {
            "stage": "vacuum_stream",
            "flux": float(sum(packet.phi_stream)),
            "trace": float(packet.information_trace),
        },
    ]
    return {"stages": stages}


def branch_simplex(*, choices: int = 5) -> dict[str, Any]:
    i = information_tensor_N(choices, np.ones(4) * 0.1)
    tr = compute_information_trace(i)
    weights = np.ones(choices) / choices
    return {
        "choices": choices,
        "weights": weights.tolist(),
        "entropy_trace": tr,
        "labels": [f"branch_{k}" for k in range(choices)],
    }


def falsification_panel() -> dict[str, Any]:
    suite = load_cached_suite() or prove_all(save=True)
    proof_map = {r.id: r.passed for r in suite.results}
    report_data: dict[str, Any] = {}
    latest = latest_report()
    if latest is not None:
        rep = load_report(latest)
        report_data = {
            "rble_score": rep.rble_score,
            "null_sigma": rep.null_sigma,
            "flags": rep.falsification_flags,
            "path": str(latest),
        }
    return {
        "p1": proof_map.get("fals_p1", False),
        "p2": proof_map.get("fals_p2", False),
        "p3": proof_map.get("fals_p3", False),
        "proofs_all_passed": suite.all_passed,
        "report": report_data,
        "superpotential_sample": float(abs(superpotential_W([1, 0, -1]))),
    }
