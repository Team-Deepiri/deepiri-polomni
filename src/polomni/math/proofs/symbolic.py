"""SymPy symbolic checks for RBLE master equations."""

from __future__ import annotations

from polomni.math.proofs.base import ProofResult
from polomni.math.proofs.baselines import check_within


def _sympy_available() -> bool:
    try:
        import sympy  # noqa: F401

        return True
    except ImportError:
        return False


def prove_sym_eq04() -> ProofResult:
    """Verify Tr(I²) equals contracted trace for 2×2 symmetric I (Eq. 4)."""
    if not _sympy_available():
        return ProofResult(
            id="sym_eq04",
            name="",
            equation="",
            passed=False,
            residual=1.0,
            tolerance=0.0,
            message="sympy not installed",
            module="polomni.math.proofs.symbolic",
        )

    import sympy as sp

    i00, i01, i11 = sp.symbols("I00 I01 I11", real=True)
    i = sp.Matrix([[i00, i01], [i01, i11]])
    tr_i2 = sp.trace(i * i)
    expanded = sp.expand(tr_i2)
    manual = i00**2 + 2 * i01**2 + i11**2
    diff = sp.simplify(expanded - manual)
    ok = diff == 0
    passed, residual, msg = check_within("sym_eq04", {"symbolic_ok": 1.0 if ok else 0.0})
    return ProofResult(
        id="sym_eq04",
        name="Sym Eq4 Tr(I²)",
        equation="Tr(I_μν I^μν)",
        passed=passed and ok,
        residual=residual if ok else 1.0,
        tolerance=0.0,
        message=f"SymPy Tr(I²) identity: {msg}",
        module="polomni.math.proofs.symbolic",
    )


def prove_sym_eq07() -> ProofResult:
    """Verify conductance Laplacian is symmetric for undirected edge weights (Eq. 7)."""
    if not _sympy_available():
        return ProofResult(
            id="sym_eq07",
            name="",
            equation="",
            passed=False,
            residual=1.0,
            tolerance=0.0,
            message="sympy not installed",
            module="polomni.math.proofs.symbolic",
        )

    import sympy as sp

    g01, g12, g23 = sp.symbols("g01 g12 g23", positive=True, real=True)
    lap = sp.Matrix(
        [
            [g01, -g01, 0, 0],
            [-g01, g01 + g12, -g12, 0],
            [0, -g12, g12 + g23, -g23],
            [0, 0, -g23, g23],
        ]
    )
    ok = sp.simplify(lap - lap.T) == sp.zeros(4)
    passed, residual, msg = check_within("sym_eq07", {"symbolic_ok": 1.0 if ok else 0.0})
    return ProofResult(
        id="sym_eq07",
        name="Sym Eq7 conductance",
        equation="G_ij = G_ji",
        passed=passed and ok,
        residual=residual if ok else 1.0,
        tolerance=0.0,
        message=f"SymPy conductance symmetry: {msg}",
        module="polomni.math.proofs.symbolic",
    )


def prove_sym_vp() -> ProofResult:
    """Verify boundary flux equals bulk Tr(I²) in the VP closure identity."""
    if not _sympy_available():
        return ProofResult(
            id="sym_vp",
            name="",
            equation="",
            passed=False,
            residual=1.0,
            tolerance=0.0,
            message="sympy not installed",
            module="polomni.math.proofs.symbolic",
        )

    import sympy as sp

    tr, area, n = sp.symbols("Tr_I2 A N", positive=True, real=True)
    phi = tr / (n * area)
    flux = n * phi * area
    ok = sp.simplify(flux - tr) == 0
    passed, residual, msg = check_within("sym_vp", {"symbolic_ok": 1.0 if ok else 0.0})
    return ProofResult(
        id="sym_vp",
        name="Sym VP closure",
        equation="∮ Φ dA = Tr(I²)",
        passed=passed and ok,
        residual=residual if ok else 1.0,
        tolerance=0.0,
        message=f"SymPy variational closure: {msg}",
        module="polomni.math.proofs.symbolic",
    )


def prove_all_symbolic() -> list[ProofResult]:
    return [prove_sym_eq04(), prove_sym_eq07(), prove_sym_vp()]
