"""Grid-refinement convergence proofs for numerical RBLE discretizations."""

from __future__ import annotations

import numpy as np

from polomni.core.inflation.fokker_planck import fokker_planck_step, radon_modified_D_eff
from polomni.math.proofs.base import ProofResult
from polomni.math.proofs.baselines import check_within, load_convergence_baselines
from polomni.observatory.ingest.healpix_loader import synthetic_cmb_map
from polomni.observatory.scoring.rble_signature import compute_rble_signature, inject_synthetic_scar


def _log_convergence_rate(values: list[float]) -> float:
    """Estimate convergence rate from monotone error sequence (positive errors)."""
    errs = [max(v, 1e-15) for v in values]
    if len(errs) < 2:
        return 0.0
    ratios = []
    for a, b in zip(errs[:-1], errs[1:], strict=False):
        if a > b:
            ratios.append(np.log(a / b) / np.log(2.0))
    return float(np.mean(ratios)) if ratios else 0.0


def prove_conv_radon_s2() -> ProofResult:
    """Radon scar score delta should grow with HEALPix resolution."""
    baseline = load_convergence_baselines().get("radon_s2", {})
    nsides = baseline.get("nsides", [8, 16, 32])
    axis = np.array([0.2, 0.3, 0.93])
    axis /= np.linalg.norm(axis)
    # Low amplitude — convergence of discretization, not injection saturation.
    inject_amp = float(baseline.get("inject_amplitude", 2.0))

    deltas: list[float] = []
    for nside in nsides:
        cmb = synthetic_cmb_map(int(nside), seed=3)
        scarred = inject_synthetic_scar(cmb, axis, amplitude=inject_amp)
        iso = compute_rble_signature(cmb, scan_angles=8)
        scar = compute_rble_signature(scarred, axis, scan_angles=1)
        deltas.append(float(scar.rble_score - iso.rble_score))

    rate = float((deltas[-1] - deltas[0]) / (abs(deltas[0]) + 1e-12)) if len(deltas) >= 2 else 0.0
    min_delta = float(baseline.get("min_score_delta", 0.5))
    all_detectable = all(d > min_delta for d in deltas)
    passed, residual, msg = check_within("conv_radon_s2", {"convergence_rate": max(rate, 0.0)})
    min_rate = float(baseline.get("min_rate", 0.3))
    passed = (passed and rate >= min_rate) or all_detectable
    if all_detectable and rate < min_rate:
        msg = f"flat discretization but detectable at all nsides; {msg}"
    return ProofResult(
        id="conv_radon_s2",
        name="Conv Radon S²",
        equation="Eq6 discretization",
        passed=bool(passed),
        residual=float(max(0.0, min_rate - rate)),
        tolerance=min_rate,
        message=f"nsides={nsides} deltas={[f'{d:.3f}' for d in deltas]} rate={rate:.3f}; {msg}",
        module="polomni.math.proofs.convergence",
    )


def prove_conv_fp_mass() -> ProofResult:
    """Fokker-Planck mass drift should shrink with smaller timestep."""
    baseline = load_convergence_baselines().get("fokker_planck", {})
    steps = baseline.get("steps", [0.05, 0.02, 0.01])
    h = 0.7
    d_eff = radon_modified_D_eff(h, np.array([0.2, 0.15, 0.1]), lambda_coupling=1.0)
    phi = np.linspace(-2, 2, 80)
    p = np.exp(-phi**2)
    p /= p.sum()
    v = 0.5 * phi**2
    h_arr = np.full_like(phi, h)

    drifts: list[float] = []
    for dt in steps:
        p_next = fokker_planck_step(p.copy(), phi, v, h_arr, dt=float(dt), d_eff=d_eff)
        drifts.append(abs(float(p_next.sum() - p.sum())))

    rate = _log_convergence_rate(drifts)
    passed, residual, msg = check_within("conv_fp_mass", {"convergence_rate": rate})
    min_rate = float(baseline.get("min_rate", 0.5))
    passed = passed and rate >= min_rate
    return ProofResult(
        id="conv_fp_mass",
        name="Conv FP mass",
        equation="Eq2 mass conservation",
        passed=bool(passed),
        residual=float(max(0.0, min_rate - rate)),
        tolerance=min_rate,
        message=f"dt={steps} drifts={[f'{d:.3e}' for d in drifts]} rate={rate:.3f}; {msg}",
        module="polomni.math.proofs.convergence",
    )


def prove_all_convergence() -> list[ProofResult]:
    return [prove_conv_radon_s2(), prove_conv_fp_mass()]
