"""Optional adapter for RemoteField / SZ_cosmo multi-z tomography.

Phase F (`multi_z_tomography.py`) implements in-repo multi-z Fisher stacking on
PSCz Hvel→z shells with Deutsch/Cai-style radial kernel weights — no vendor clone.

Full RemoteField (Cai et al. 2025) computes 3D RDF/RQF from primordial potential
Ψ_i(k) using FFT + SZ_cosmo kernels. When a checkout exists under vendor/, future
work can export 2D sky shells → HEALPix → `match_cai_bubble_template`.

Until then: `polomni data rdf-tomography` runs Phase A–F in-process.
"""

from __future__ import annotations

from pathlib import Path


def remote_field_available(root: Path | None = None) -> bool:
    """True if an external RemoteField checkout exists."""
    root = root or Path("vendor/RemoteField")
    return (root / "RemoteField").exists() or (root / "remote_field.py").exists()


def phase_f_in_repo() -> bool:
    """In-repo multi-z tomography is always available (PSCz Hvel bins)."""
    return True
