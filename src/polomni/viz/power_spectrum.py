"""CMB power spectrum plots."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot_power_spectrum(
    ell: np.ndarray,
    dl: np.ndarray,
    *,
    title: str = "CMB TT Power Spectrum",
    save_path: str | Path | None = None,
) -> Path:
    """Plot D_l vs ell and save PNG."""
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(ell, dl, color="#4fc3f7", linewidth=1.2)
    ax.set_xlabel(r"Multipole $\ell$")
    ax.set_ylabel(r"$D_\ell$ [$\mu$K$^2$]")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if save_path is None:
        save_path = Path("data/figures/power_spectrum.png")
    out = Path(save_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out
