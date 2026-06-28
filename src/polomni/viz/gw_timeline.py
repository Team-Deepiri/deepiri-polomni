"""Gravitational-wave event timeline plots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_gw_timeline(
    events: list[dict[str, Any]],
    *,
    title: str = "GWTC Event Timeline",
    save_path: str | Path | None = None,
    limit: int = 50,
) -> Path:
    """Bar chart of GW events (most recent first)."""
    subset = events[:limit]
    names = [e.get("name", e.get("id", f"evt-{i}")) for i, e in enumerate(subset)]
    masses = [
        float(e.get("mass_1", e.get("mass1", 0)) or 0) + float(e.get("mass_2", e.get("mass2", 0)) or 0)
        for e in subset
    ]
    if not masses or max(masses) <= 0:
        masses = list(range(len(subset), 0, -1))

    fig, ax = plt.subplots(figsize=(10, max(4, len(subset) * 0.2)))
    y_pos = range(len(names))
    ax.barh(list(y_pos), masses, color="#ff7043", alpha=0.85)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(names, fontsize=7)
    ax.set_xlabel("Total mass proxy (M☉)")
    ax.set_title(title)
    ax.invert_yaxis()
    fig.tight_layout()

    if save_path is None:
        save_path = Path("data/figures/gw_timeline.png")
    out = Path(save_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out
