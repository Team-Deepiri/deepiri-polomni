"""Batch closed-loop runs for neural corpus generation."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from polomni.core.superspace.district_graph import ChoicePolicy
from polomni.integration.loop_logger import run_and_log_loop


@dataclass
class BatchLoopResult:
    """Summary of a batch corpus generation run."""

    n_runs: int
    paths: list[str]
    mean_final_error_deg: float
    output_dir: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_runs": self.n_runs,
            "paths": self.paths,
            "mean_final_error_deg": self.mean_final_error_deg,
            "output_dir": self.output_dir,
        }


def _single_run(args: tuple[int, int, int, int, str, str]) -> tuple[str, float]:
    seed, steps, choices, nside, policy, out = args
    _, results, path = run_and_log_loop(
        steps=steps,
        num_choices=choices,
        nside=nside,
        seed=seed,
        policy=ChoicePolicy(policy),
        output_dir=Path(out),
    )
    err = results[-1].axis_error_deg if results else 0.0
    return str(path), err


def run_loop_batch(
    *,
    count: int = 10,
    steps: int = 3,
    num_choices: int = 4,
    nside: int = 32,
    base_seed: int = 0,
    policy: ChoicePolicy = ChoicePolicy.AXIS_BIASED,
    output_dir: Path | None = None,
    workers: int = 1,
) -> BatchLoopResult:
    """Run *count* independent closed loops and log each to JSON."""
    out = output_dir or Path("data/loop_runs")
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    errors: list[float] = []

    jobs = [
        (base_seed + i, steps, num_choices, nside, policy.value, str(out))
        for i in range(count)
    ]

    if workers <= 1:
        for job in jobs:
            path, err = _single_run(job)
            paths.append(path)
            errors.append(err)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_single_run, job) for job in jobs]
            for fut in as_completed(futures):
                path, err = fut.result()
                paths.append(path)
                errors.append(err)

    return BatchLoopResult(
        n_runs=len(paths),
        paths=paths,
        mean_final_error_deg=float(sum(errors) / max(len(errors), 1)),
        output_dir=str(out),
    )
