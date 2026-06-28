"""RBLE equation catalog for API and CLI."""

EQUATION_CATALOG: list[dict[str, str]] = [
    {"id": "VP", "name": "Master action S_RBLE", "module": "polomni.math.proofs.variational"},
    {"id": "Eq1", "name": "Informational-string Einstein", "module": "polomni.core.gravity.field_equations"},
    {"id": "Eq2", "name": "Radon-rotated Fokker-Planck", "module": "polomni.core.inflation.fokker_planck"},
    {"id": "Eq3", "name": "WDW bifurcation closure", "module": "polomni.core.superspace.wdw_generator"},
    {"id": "Eq4", "name": "Choice entropy continuity", "module": "polomni.core.conservation"},
    {"id": "Eq5", "name": "Radon-modulated FP full", "module": "polomni.core.inflation.drift_diffusion"},
    {"id": "Eq6", "name": "Spherical Radon scar S^2", "module": "polomni.core.radon.transform_s2"},
    {"id": "Eq7", "name": "ER=EPR conductance", "module": "polomni.core.conductance.bridge_tensor"},
    {"id": "Eq8", "name": "Kahler stabilization", "module": "polomni.core.landscape.kahler"},
    {"id": "P1", "name": "CMB scar falsification", "module": "polomni.observatory.scoring"},
    {"id": "P2", "name": "Directed diffusion falsification", "module": "polomni.core.inflation"},
    {"id": "P3", "name": "GW conductance falsification", "module": "polomni.core.conductance"},
]
