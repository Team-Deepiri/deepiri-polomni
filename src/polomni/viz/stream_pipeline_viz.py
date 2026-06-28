"""Radon vacuum stream pipeline visualization."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot_stream_pipeline(
    stages: Sequence[dict[str, Any] | float],
    *,
    title: str = "Radon Vacuum Stream Pipeline",
    ax: Any | None = None,
    show: bool = False,
    save_path: str | Path | None = None,
) -> Any:
    """Plot flux values across Radon pipeline stages.

    Parameters
    ----------
    stages:
        Sequence of stage dicts with ``name`` and ``flux`` keys, or numeric flux values.
    title:
        Plot title.
    ax:
        Optional matplotlib axes.
    show:
        Call ``plt.show()`` when True.
    save_path:
        When set, save the figure to this path.

    Returns
    -------
    matplotlib axes.
    """
    names: list[str] = []
    fluxes: list[float] = []

    for i, stage in enumerate(stages):
        if isinstance(stage, dict):
            names.append(str(stage.get("name", f"stage_{i}")))
            fluxes.append(float(stage.get("flux", 0.0)))
        else:
            names.append(f"stage_{i}")
            fluxes.append(float(stage))

    created_fig = ax is None
    if created_fig:
        fig, ax = plt.subplots(figsize=(9, 4))
    else:
        fig = ax.figure

    x = np.arange(len(names))
    bars = ax.bar(x, fluxes, color="teal", alpha=0.8, edgecolor="black")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=25, ha="right")
    ax.set_ylabel("Phi_stream flux")
    ax.set_title(title)
    ax.axhline(0, color="black", linewidth=0.5)

    for bar, val in zip(bars, fluxes, strict=False):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{val:.3e}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    if save_path is not None:
        out = Path(save_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=150, bbox_inches="tight")
        if not show:
            plt.close(fig)

    if show:
        plt.show()
    return ax
