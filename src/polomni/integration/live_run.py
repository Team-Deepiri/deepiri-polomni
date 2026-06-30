"""Real-data live pipeline: fetch → gates → P1 study → physics-loop convergence."""

from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from polomni.integration.real_sky_bridge import PhysicsLoopResult, run_physics_loop
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.catalog import get_product
from polomni.observatory.pipeline.downloader import fetch_product
from polomni.observatory.studies.gates import GateReport, run_p1_gates
from polomni.observatory.studies.p1_runner import run_p1_study

_STUDY_MAPS = ("wmap_k_band", "planck_smica_cmb")
_LIVE_RUNS_DIR = Path("data/studies/live_runs")


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def ensure_study_maps(cache: DataCache | None = None, *, force_fetch: bool = False) -> list[str]:
    """Fetch WMAP + Planck holdout maps if missing from cache."""
    cache = cache or DataCache()
    fetched: list[str] = []
    for product_id in _STUDY_MAPS:
        if not force_fetch and cache.resolved_path(product_id) is not None:
            continue
        product = get_product(product_id)
        result = fetch_product(product, cache=cache, force=force_fetch)
        if result.downloaded or result.from_cache:
            fetched.append(product_id)
    return fetched


def log_physics_loop_run(result: PhysicsLoopResult, *, output_dir: Path | None = None) -> Path:
    """Persist physics-loop convergence telemetry for sim ↔ real axis analysis."""
    output_dir = output_dir or _LIVE_RUNS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:12]
    separations = [s.separation_deg for s in result.steps]
    improving = (
        len(separations) >= 2 and separations[-1] < separations[0]
        if separations
        else None
    )
    payload: dict[str, Any] = {
        "run_id": run_id,
        "kind": "physics_loop",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "map_product_id": result.map_product_id,
        "nside": result.nside,
        "real_axis": result.real_axis,
        "real_score": result.real_score,
        "steps": [s.to_dict() for s in result.steps],
        "final_separation_deg": result.steps[-1].separation_deg if result.steps else None,
        "convergence_improving": improving,
    }
    path = output_dir / f"{run_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


@dataclass
class LiveRunReport:
    """Unified real-data live run report."""

    fetched_products: list[str] = field(default_factory=list)
    gates: GateReport | None = None
    calibration: dict[str, Any] | None = None
    blind: dict[str, Any] | None = None
    physics: dict[str, Any] | None = None
    physics_log_path: str | None = None
    convergence_improving: bool | None = None
    converged_to_real: bool | None = None
    elapsed_seconds: float = 0.0

    @property
    def ready_for_holdout(self) -> bool:
        return bool(self.gates and self.gates.all_passed and self.calibration is not None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fetched_products": self.fetched_products,
            "gates": self.gates.to_dict() if self.gates else None,
            "calibration": self.calibration,
            "blind": self.blind,
            "physics": self.physics,
            "physics_log_path": self.physics_log_path,
            "convergence_improving": self.convergence_improving,
            "converged_to_real": self.converged_to_real,
            "ready_for_holdout": self.ready_for_holdout,
            "elapsed_seconds": self.elapsed_seconds,
        }


def run_live_pipeline(
    *,
    fetch: bool = True,
    run_gates: bool = True,
    run_calibration: bool = True,
    run_blind: bool = False,
    run_physics: bool = True,
    physics_steps: int = 3,
    physics_nside: int = 64,
    gate_trials: int = 8,
    cache: DataCache | None = None,
    output_path: Path | None = None,
) -> LiveRunReport:
    """End-to-end real-data path toward P1 + sim↔real convergence."""
    import time

    t0 = time.perf_counter()
    cache = cache or DataCache()
    report = LiveRunReport()

    if fetch:
        report.fetched_products = ensure_study_maps(cache)

    missing = [p for p in _STUDY_MAPS if cache.resolved_path(p) is None]
    if missing:
        msg = f"Missing cached maps {missing}; run with fetch=True or polomni data fetch --wmap --planck"
        raise FileNotFoundError(msg)

    if run_gates:
        report.gates = run_p1_gates(injection_trials=gate_trials)

    if run_calibration:
        report.calibration = run_p1_study(cache=cache, blind=False, calibration=True)

    if run_blind:
        if not report.ready_for_holdout and run_gates and not (report.gates and report.gates.all_passed):
            msg = "Gates must pass before blind holdout — fix calibration pipeline first"
            raise RuntimeError(msg)
        report.blind = run_p1_study(cache=cache, blind=True, calibration=False)

    if run_physics:
        physics = run_physics_loop(
            steps=physics_steps,
            nside=physics_nside,
            map_product_id="wmap_k_band",
            cache=cache,
        )
        log_path = log_physics_loop_run(physics)
        report.physics = physics.to_dict()
        report.physics_log_path = str(log_path.resolve())
        steps = physics.steps
        if len(steps) >= 2:
            report.convergence_improving = steps[-1].separation_deg < steps[0].separation_deg
        if steps:
            report.converged_to_real = steps[-1].separation_deg < 10.0

    report.elapsed_seconds = time.perf_counter() - t0

    out = output_path or Path("data/reports/live_run.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return report
