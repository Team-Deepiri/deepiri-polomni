"""Unified falsification runner: P1–P3 on synthetic and real cached data."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from polomni.math.proofs.base import ProofResult
from polomni.math.proofs.falsification import prove_p1, prove_p2, prove_p3
from polomni.math.proofs.real_data import cache_ready, prove_all_real_data
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.processor import ingest_standard_data

_FALSIFY_CACHE = Path("data/proofs/falsification_latest.json")


@dataclass
class FalsificationReport:
    """Combined synthetic + optional real-data falsification report."""

    ran_at: datetime
    mode: str
    synthetic: list[ProofResult] = field(default_factory=list)
    real: list[ProofResult] = field(default_factory=list)
    data_ready: bool = False
    fetched: bool = False

    @property
    def all_results(self) -> list[ProofResult]:
        return self.synthetic + self.real

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.all_results if r.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for r in self.all_results if not r.passed)

    @property
    def all_passed(self) -> bool:
        return self.failed_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ran_at": self.ran_at.isoformat(),
            "mode": self.mode,
            "data_ready": self.data_ready,
            "fetched": self.fetched,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "all_passed": self.all_passed,
            "synthetic": [r.to_dict() for r in self.synthetic],
            "real": [r.to_dict() for r in self.real],
            "flags": {
                "P1": _flag("P1", self.all_results),
                "P2": _flag("P2", self.all_results),
                "P3": _flag("P3", self.all_results),
            },
        }

    def save(self, path: Path | None = None) -> Path:
        path = path or _FALSIFY_CACHE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path


def _flag(label: str, results: list[ProofResult]) -> bool:
    hits = [r for r in results if label.lower() in r.id.lower() or label in r.name]
    return all(r.passed for r in hits) if hits else False


def run_falsification(
    *,
    real: bool = False,
    fetch: bool = False,
    cache: DataCache | None = None,
    target_nside: int = 128,
    save: bool = True,
) -> FalsificationReport:
    """Run falsification trinity; optionally verify on cached cosmology products."""
    cache = cache or DataCache()
    fetched = False
    if fetch:
        ingest_standard_data(cache, include_heavy=False, force=False, fetch_gw=True)
        fetched = True

    synthetic = [prove_p1(), prove_p2(), prove_p3()]
    real_results: list[ProofResult] = []
    ready = cache_ready(cache)

    if real:
        if ready:
            real_results = prove_all_real_data(cache, target_nside=target_nside)
        else:
            real_results = [
                ProofResult(
                    id="real_data",
                    name="Real data cache",
                    equation="",
                    passed=False,
                    residual=float("inf"),
                    tolerance=0.0,
                    message="Cache incomplete; run: polomni falsify --real --fetch",
                    module="polomni.math.falsification_runner",
                )
            ]

    mode = "real+synthetic" if real else "synthetic"
    report = FalsificationReport(
        ran_at=datetime.now(timezone.utc),
        mode=mode,
        synthetic=synthetic,
        real=real_results,
        data_ready=ready,
        fetched=fetched,
    )
    if save:
        report.save()
    return report
