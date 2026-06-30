"""GW ringdown phase correlation and conductance graph wiring."""

from __future__ import annotations

from typing import Any

import numpy as np

from polomni.core.superspace.district_graph import DistrictGraph
from polomni.observatory.pipeline.sources.gwosc import GWEvent


def synthetic_ringdown_phases(
  events: list[GWEvent],
    *,
    seed: int = 0,
    n_modes: int = 3,
) -> dict[str, np.ndarray]:
    """Assign synthetic ringdown phase vectors for testing P3 conductance links."""
    rng = np.random.default_rng(seed)
    phases: dict[str, np.ndarray] = {}
    for event in events:
        phases[event.name] = rng.uniform(0, 2 * np.pi, size=n_modes)
    return phases


def phase_correlation(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine correlation between ringdown phase vectors."""
    a = np.asarray(a, dtype=float).ravel()
    b = np.asarray(b, dtype=float).ravel()
    n = min(a.size, b.size)
    if n == 0:
        return 0.0
    a, b = a[:n], b[:n]
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-15))


def correlate_gw_phases(
    events: list[GWEvent],
    phases: dict[str, np.ndarray],
    linked_pairs: list[tuple[str, str]],
    unlinked_pairs: list[tuple[str, str]],
) -> dict[str, Any]:
    """Compare phase correlations for conductance-linked vs unlinked event pairs."""
    linked_rho = [
        phase_correlation(phases[a], phases[b])
        for a, b in linked_pairs
        if a in phases and b in phases
    ]
    unlinked_rho = [
        phase_correlation(phases[a], phases[b])
        for a, b in unlinked_pairs
        if a in phases and b in phases
    ]
    return {
        "linked_mean": float(np.mean(linked_rho)) if linked_rho else 0.0,
        "unlinked_mean": float(np.mean(unlinked_rho)) if unlinked_rho else 0.0,
        "linked_count": len(linked_rho),
        "unlinked_count": len(unlinked_rho),
        "excess_correlation": (
            float(np.mean(linked_rho) - np.mean(unlinked_rho))
            if linked_rho and unlinked_rho
            else 0.0
        ),
    }


def wire_gw_to_conductance(
    graph: DistrictGraph,
    gw_matches: list[dict[str, Any]],
    *,
    scale: float = 0.01,
) -> list[dict[str, Any]]:
    """Boost portal edge conductance when GW events align with district axes.

    *gw_matches* entries should include ``name`` and ``separation_deg`` from
    :func:`polomni.observatory.pipeline.processor.correlate_gw_rble`.
    """
    updates: list[dict[str, Any]] = []
    if not gw_matches:
        return updates

    for u, v, data in list(graph.graph.edges(data=True)):
        old_g = float(data.get("conductance", 0.0))
        boost = 0.0
        for match in gw_matches:
            sep = float(match.get("separation_deg", 90.0))
            boost += scale * max(0.0, 1.0 - sep / 30.0)
        new_g = old_g + boost
        graph.set_conductance(u, v, new_g)
        updates.append(
            {
                "edge": [int(u), int(v)],
                "old_conductance": old_g,
                "new_conductance": new_g,
                "gw_boost": boost,
            }
        )
    return updates


def build_synthetic_gw_test(
    graph: DistrictGraph,
    event_names: list[str],
    *,
    seed: int = 0,
) -> dict[str, Any]:
    """End-to-end synthetic P3 test from district graph edges."""
    events = [
        GWEvent(name=n, gps=1000000.0 + i, catalog="synthetic", detectors=["H1", "L1"], network_axis=None)
        for i, n in enumerate(event_names)
    ]
    phases = synthetic_ringdown_phases(events, seed=seed)
    edges = list(graph.graph.edges())
    if len(edges) < 2 or len(event_names) < 2:
        return {"status": "insufficient_data"}

    linked = [(event_names[0], event_names[1])]
    unlinked = [(event_names[0], event_names[-1])] if len(event_names) > 2 else linked
    # Inject correlated phases for linked pair (same parent choice node).
    if linked[0][0] in phases and linked[0][1] in phases:
        base = phases[linked[0][0]]
        phases[linked[0][1]] = base + np.random.default_rng(seed).normal(0, 0.05, base.shape)

    stats = correlate_gw_phases(events, phases, linked, unlinked)
    return {"phases": {k: v.tolist() for k, v in phases.items()}, "stats": stats}
