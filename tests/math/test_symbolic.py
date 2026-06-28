"""Tests for SymPy symbolic proof modules."""

from polomni.math.proofs.symbolic import prove_all_symbolic


def test_symbolic_proofs_pass() -> None:
    results = prove_all_symbolic()
    assert len(results) == 3
    assert all(r.passed for r in results)
