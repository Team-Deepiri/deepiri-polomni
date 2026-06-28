"""Cosmos verification runner with live progress events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from polomni.math.proofs.base import prove_all
from polomni.observatory.studies.gates import run_p1_gates
from polomni.observatory.studies.p1_runner import run_p1_study
from polomni.viz.cosmos.analytics import dual_map_comparison, null_score_histogram, sky_payload_cached
from polomni.viz.cosmos.serializers import (
    cached_gate_report,
    cosmos_null_tiers_payload,
    cosmos_power_spectrum_payload,
    load_real_sky_map,
)

_progress: list[dict[str, Any]] = []
_running = False


def progress_events() -> list[dict[str, Any]]:
    return list(_progress)


def is_running() -> bool:
    return _running


def clear_progress() -> None:
    _progress.clear()


def _push(step: str, message: str, **extra: Any) -> None:
    _progress.append(
        {
            "step": step,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **extra,
        }
    )


def run_full_verification(
    *,
    blind: bool = False,
    strict_prove: bool = True,
) -> dict[str, Any]:
    """Run gates + strict proofs + P1 study with progress log."""
    global _running
    _running = True
    clear_progress()
    started = datetime.now(timezone.utc)
    _push("start", f"Verification started (blind={blind})")

    try:
        _push("gates", "Running Gates 1–3 (injection recovery + cache check)…")
        gates = run_p1_gates(injection_trials=30)
        cached_gate_report(refresh=True)
        _push(
            "gates_done",
            f"Gates {gates.passed_count}/{len(gates.checks)} passed",
            passed=gates.all_passed,
        )

        proof_suite = None
        if strict_prove:
            _push("proofs", "Running strict real-data proof suite (23 checks)…")
            proof_suite = prove_all(save=True, strict=True, real_data=True)
            _push(
                "proofs_done",
                f"Proofs {proof_suite.passed_count}/{len(proof_suite.results)} passed",
                all_passed=proof_suite.all_passed,
            )

        mode = "holdout_blind" if blind else "calibration"
        _push("study", f"Running P1 study ({mode})…")
        study = run_p1_study(blind=blind, calibration=not blind)
        _push(
            "study_done",
            f"P1 study complete — supported={study.get('p1_supported')}",
            p1_supported=study.get("p1_supported"),
            p1_falsified=study.get("p1_falsified"),
            score=study.get("detection", {}).get("rble_score"),
        )

        _push("viz", "Building dual-map comparison and null histogram…")
        compare = dual_map_comparison(nside=64)
        cmb, pid, _ = load_real_sky_map(
            map_product_id=str(study.get("map_product_id", "wmap_k_band")),
            nside=64,
        )
        histogram = null_score_histogram(cmb, n_ensemble=35, seed=9)
        _push("viz_done", "Visualization payloads ready")

        result = {
            "started_at": started.isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "gates": gates.to_dict(),
            "proofs": proof_suite.to_dict() if proof_suite else None,
            "study": study,
            "compare": compare,
            "histogram": histogram,
            "sky": sky_payload_cached(nside=64, force=True),
            "power_spectrum": cosmos_power_spectrum_payload(),
            "null_tiers": cosmos_null_tiers_payload(nside=64, n_ensemble=20),
        }
        _push("complete", "Verification finished", ok=True)
        return result
    except Exception as exc:
        _push("error", str(exc), ok=False)
        raise
    finally:
        _running = False
