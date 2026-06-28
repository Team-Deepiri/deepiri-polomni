"""District graph visualization."""

from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


def plot_district_graph(
    graph: nx.DiGraph | Any,
    *,
    title: str = "District Graph",
    ax: Any | None = None,
    show: bool = False,
) -> Any:
    """Plot a district DAG (NetworkX DiGraph or DistrictGraph with .graph attr).

    Parameters
    ----------
    graph:
        ``networkx.DiGraph`` or object exposing ``.graph`` DiGraph.
    title:
        Plot title.
    ax:
        Optional matplotlib axes.
    show:
        Call ``plt.show()`` when True.

    Returns
    -------
    matplotlib axes.
    """
    if hasattr(graph, "graph"):
        g = graph.graph
    else:
        g = graph

    if ax is None:
        _, ax = plt.subplots(figsize=(8, 6))

    pos = nx.spring_layout(g, seed=42)
    masses = [g.nodes[n].get("mass", 1.0) for n in g.nodes]
    sizes = 300 * np.array(masses) / (max(masses) + 1e-12)

    nx.draw_networkx_nodes(g, pos, node_size=sizes, node_color="steelblue", alpha=0.85, ax=ax)
    nx.draw_networkx_edges(g, pos, arrows=True, arrowsize=15, edge_color="gray", ax=ax)
    labels = {n: str(n)[:8] for n in g.nodes}
    nx.draw_networkx_labels(g, pos, labels=labels, font_size=8, ax=ax)
    ax.set_title(title)
    ax.axis("off")

    if show:
        plt.show()
    return ax
