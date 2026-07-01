"""P1 study gate checks (Gates 1–3 before holdout)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.scoring.hierarchical_search import hierarchical_sky_search
from polomni.observatory.scoring.rble_signature import compute_rble_signature, inject_synthetic_scar
from polomni.observatory.studies.config import P1StudyConfig, load_p1_config
from polomni.observatory.studies.replication import run_independent_replication


@dataclass
class GateCheck:
    gate: str
    name: str
    passed: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class GateReport:
    checks: list[GateCheck] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "all_passed": self.all_passed,
            "passed": self.passed_count,
            "failed": len(self.checks) - self.passed_count,
            "checks": [
                {
                    "gate": c.gate,
                    "name": c.name,
                    "passed": c.passed,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
        }


def _axis_error_deg(true_axis: np.ndarray, recovered: list[float]) -> float:
    a = np.asarray(recovered, dtype=float)
    a /= np.linalg.norm(a) + 1e-15
    t = true_axis / (np.linalg.norm(true_axis) + 1e-15)
    dot = float(np.clip(np.dot(a, t), -1.0, 1.0))
    return float(np.degrees(np.arccos(abs(dot))))


def check_gate1_config(config_path: Path | None = None) -> GateCheck:
    try:
        cfg = load_p1_config(config_path)
        prereg = Path("docs/studies/P1_CMB_RADON_SCAR_PREREG.md")
        ok = cfg.registered_before_holdout and prereg.is_file()
        return GateCheck(
            gate="G1",
            name="Pre-registration frozen",
            passed=ok,
            message=f"config v{cfg.version}, prereg={'found' if prereg.is_file() else 'MISSING'}",
            details={"study_id": cfg.study_id, "version": cfg.version},
        )
    except Exception as exc:
        return GateCheck("G1", "Pre-registration frozen", False, str(exc))


def check_gate2_injection(
    *,
    nside: int = 32,
    snr: int = 3,
    trials: int = 25,
    amplitude_map: dict[int, float] | None = None,
) -> GateCheck:
    """Quick injection recovery sample (full test in pytest -m slow)."""
    amplitude_map = amplitude_map or {1: 3.0, 2: 6.0, 3: 12.0, 5: 18.0}
    amp = amplitude_map.get(snr, 12.0)
    rng = np.random.default_rng(7)
    successes = 0
    errors: list[float] = []
    for trial in range(trials):
        axis = rng.standard_normal(3)
        axis /= np.linalg.norm(axis)
        cmb = synthetic_cmb_map(nside, seed=trial + 500)
        scarred = inject_synthetic_scar(cmb, axis, amplitude=amp)
        rep = hierarchical_sky_search(
            scarred,
            coarse_nside=min(16, nside // 2 or 16),
            refine_samples=16,
            coarse_scan_angles=16,
            seed=trial,
        )
        err = _axis_error_deg(axis, rep.preferred_axis)
        errors.append(err)
        if err < 5.0:
            successes += 1
    rate = successes / trials
    passed = rate >= 0.9
    return GateCheck(
        gate="G2",
        name="Injection recovery",
        passed=passed,
        message=f"SNR={snr} recovery {rate:.0%} ({successes}/{trials}), median err={float(np.median(errors)):.1f}°",
        details={"rate": rate, "trials": trials, "snr": snr},
    )


def check_gate3_cache(config: P1StudyConfig | None = None) -> GateCheck:
    config = config or load_p1_config()
    cache = DataCache()
    cal = str(config.maps.get("calibration_product_id", "wmap_k_band"))
    hold = str(config.maps.get("holdout_product_id", "planck_smica_cmb"))
    cal_ok = cache.resolved_path(cal) is not None
    hold_ok = cache.resolved_path(hold) is not None
    tt_ok = cache.resolved_path("planck_cmb_tt_power") is not None
    passed = cal_ok and hold_ok
    return GateCheck(
        gate="G3",
        name="Data cache ready",
        passed=passed,
        message=f"cal={cal_ok} holdout={hold_ok} planck_tt={tt_ok}",
        details={"calibration": cal, "holdout": hold, "cal_ok": cal_ok, "hold_ok": hold_ok, "tt_ok": tt_ok},
    )


def run_p1_gates(
    config_path: Path | None = None,
    *,
    injection_trials: int = 30,
) -> GateReport:
    """Run Gates 1–3 checks before blind holdout."""
    cfg = load_p1_config(config_path)
    min_snr = int(cfg.injection_calibration.get("min_snr_for_pass", 3))
    report = GateReport(
        checks=[
            check_gate1_config(config_path),
            check_gate2_injection(snr=min_snr, trials=injection_trials),
            check_gate3_cache(cfg),
        ]
    )
    return report


def load_latest_result(path: Path | None = None) -> dict[str, Any] | None:
    path = path or Path("data/studies/p1_holdout/RESULT.json")
    if not path.is_file():
        return None
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def check_gate4_blind_holdout(path: Path | None = None) -> GateCheck:
    """Gate 4: pre-registered blind holdout executed with sealed config."""
    result = load_latest_result(path)
    if result is None:
        return GateCheck(
            gate="G4",
            name="Blind holdout executed",
            passed=False,
            message="No RESULT.json — run: polomni study run p1 --blind",
        )
    blind = bool(result.get("blind"))
    holdout = result.get("map_product_id") == "planck_smica_cmb"
    has_tiers = bool(result.get("null_tier_comparison", {}).get("tiers"))
    tiers = result.get("null_tier_comparison", {}).get("tiers", {})
    n_tiers = len(tiers)
    passed = blind and holdout and has_tiers and n_tiers >= 3
    verdict = "SUPPORTED" if result.get("p1_supported") else "FALSIFIED"
    return GateCheck(
        gate="G4",
        name="Blind holdout executed",
        passed=passed,
        message=(
            f"P1 {verdict} on {result.get('map_product_id')} "
            f"S={result['detection']['rble_score']:.4f} "
            f"null_tiers={n_tiers}"
        ),
        details={
            "p1_supported": result.get("p1_supported"),
            "p1_falsified": result.get("p1_falsified"),
            "ran_at": result.get("ran_at"),
            "git_sha": result.get("git_sha"),
        },
    )


def check_gate5_replication(*, rerun: bool = False) -> GateCheck:
    """Gate 5: independent replication matches golden holdout within tolerance."""
    try:
        report = run_independent_replication(rerun=rerun)
        passed = bool(report.get("passed"))
        obs = report.get("observed", {})
        return GateCheck(
            gate="G5",
            name="Independent replication",
            passed=passed,
            message=(
                f"cache_ok={report.get('cache_checksums_ok')} "
                f"holdout_ok={report.get('holdout_match_ok')} "
                f"S={obs.get('rble_score', 0):.4f}"
            ),
            details=report,
        )
    except Exception as exc:
        return GateCheck(
            gate="G5",
            name="Independent replication",
            passed=False,
            message=str(exc),
        )


def run_p1_gates_full(
    config_path: Path | None = None,
    *,
    injection_trials: int = 30,
    require_blind: bool = False,
    require_replication: bool = False,
    replication_rerun: bool = False,
) -> GateReport:
    """Run Gates 1–4 (4 with --full) and optional Gate 5 replication."""
    report = run_p1_gates(config_path, injection_trials=injection_trials)
    if require_blind:
        report.checks.append(check_gate4_blind_holdout())
    if require_replication:
        report.checks.append(check_gate5_replication(rerun=replication_rerun))
    return report
