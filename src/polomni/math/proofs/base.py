"""Proof result types and suite runner."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_PROOF_CACHE = Path("data/proofs/latest.json")


@dataclass
class ProofResult:
    """Outcome of a single numerical or symbolic proof."""

    id: str
    name: str
    equation: str
    passed: bool
    residual: float
    tolerance: float
    message: str
    module: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MathProofSuite:
    """Collection of proof results with summary statistics."""

    ran_at: datetime
    results: list[ProofResult] = field(default_factory=list)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def all_passed(self) -> bool:
        return self.failed_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ran_at": self.ran_at.isoformat(),
            "passed": self.passed_count,
            "failed": self.failed_count,
            "all_passed": self.all_passed,
            "results": [r.to_dict() for r in self.results],
        }

    def save(self, path: Path | None = None) -> Path:
        path = path or _PROOF_CACHE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path


def _run(name: str, eq_id: str, equation: str, module: str, fn: Callable[[], ProofResult]) -> ProofResult:
    try:
        result = fn()
        result.id = eq_id
        result.name = name
        result.equation = equation
        result.module = module
        return result
    except Exception as exc:
        return ProofResult(
            id=eq_id,
            name=name,
            equation=equation,
            passed=False,
            residual=float("inf"),
            tolerance=0.0,
            message=str(exc),
            module=module,
        )


def prove_all(*, save: bool = True) -> MathProofSuite:
    """Run all RBLE equation proofs and optional falsification checks."""
    from polomni.math.proofs import (
        eq01_gravity,
        eq02_fokker_planck,
        eq03_wdw,
        eq04_conservation,
        eq05_drift_diffusion,
        eq06_radon_s2,
        eq07_conductance,
        eq08_kahler,
        falsification,
        variational,
    )

    provers: list[tuple[str, str, str, str, Callable[[], ProofResult]]] = [
        ("VP", "variational", "S_RBLE closure", "polomni.math.proofs.variational", variational.prove),
        ("Eq1", "eq01", "Einstein + I_mu_nu", "polomni.core.gravity.field_equations", eq01_gravity.prove),
        ("Eq2", "eq02", "Radon FP compact D_eff", "polomni.core.inflation.fokker_planck", eq02_fokker_planck.prove),
        ("Eq3", "eq03", "WDW bifurcation", "polomni.core.superspace.wdw_generator", eq03_wdw.prove),
        ("Eq4", "eq04", "Entropy continuity", "polomni.core.conservation", eq04_conservation.prove),
        ("Eq5", "eq05", "Directed diffusion", "polomni.core.inflation.drift_diffusion", eq05_drift_diffusion.prove),
        ("Eq6", "eq06", "Radon scar S^2", "polomni.core.radon.transform_s2", eq06_radon_s2.prove),
        ("Eq7", "eq07", "ER=EPR conductance", "polomni.core.conductance.bridge_tensor", eq07_conductance.prove),
        ("Eq8", "eq08", "Kahler stabilization", "polomni.core.landscape.kahler", eq08_kahler.prove),
        ("P1", "fals_p1", "CMB scar injection", "polomni.observatory.scoring", falsification.prove_p1),
        ("P2", "fals_p2", "Directed D_eff > D_std", "polomni.core.inflation", falsification.prove_p2),
        ("P3", "fals_p3", "Conductance symmetry", "polomni.core.conductance", falsification.prove_p3),
    ]

    results = [_run(name, eq_id, eq, mod, fn) for name, eq_id, eq, mod, fn in provers]
    suite = MathProofSuite(ran_at=datetime.now(timezone.utc), results=results)
    if save:
        suite.save()
    return suite


def load_cached_suite() -> MathProofSuite | None:
    if not _PROOF_CACHE.is_file():
        return None
    data = json.loads(_PROOF_CACHE.read_text(encoding="utf-8"))
    results = [ProofResult(**r) for r in data.get("results", [])]
    ran_at = datetime.fromisoformat(data["ran_at"])
    return MathProofSuite(ran_at=ran_at, results=results)
