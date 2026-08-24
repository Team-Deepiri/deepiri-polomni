"""Optional adapter for RemoteField / SZ_cosmo multi-z tomography.

RemoteField (Cai et al. 2025) computes 3D RDF/RQF from primordial potential Ψ_i(k)
using FFT + SZ_cosmo kernels. Polomni Phase D uses an in-repo harmonic MV quadratic
estimator (`quadratic_remote_field.py`) on cached Planck×PSCz until multi-z bins
and kernel tables are wired.

To integrate upstream RemoteField when available:
1. Clone https://github.com/catketchup/RemoteField (or paper supplement)
2. Clone https://github.com/rcayuso/SZ_cosmo for kernels
3. Export 2D sky RDF/RQF shells → HEALPix → `match_cai_bubble_template`

Until then, `polomni data rdf-tomography` runs Phase D in-process.
"""

from __future__ import annotations

from pathlib import Path


def remote_field_available(root: Path | None = None) -> bool:
    """True if an external RemoteField checkout exists."""
    root = root or Path("vendor/RemoteField")
    return (root / "RemoteField").exists() or (root / "remote_field.py").exists()
