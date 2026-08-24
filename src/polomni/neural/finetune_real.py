"""Fine-tune Graph-NODE on real-sky physics-loop targets."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from polomni.core.superspace.district_graph import ChoicePolicy
from polomni.integration.real_sky_bridge import run_physics_loop
from polomni.neural.datasets.loop_corpus import DEFAULT_LOOP_RUNS_DIR, load_corpus
from polomni.neural.train import (
    DEFAULT_CHECKPOINT_DIR,
    train_axis_predictor,
    train_branch_predictor,
)
from polomni.neural.scar_classifier.train_scar import train_scar_classifier
from polomni.observatory.pipeline.cache import DataCache


def generate_real_sky_training_runs(
    *,
    count: int = 20,
    steps: int = 3,
    nside: int = 32,
    map_product_id: str = "wmap_k_band",
    seed: int = 0,
    output_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Run physics loops and log steps with ``recovered_axis := real_axis``.

    That teaches the axis predictor to map district-graph features toward the
    observational preferred axis — the transfer step from synthetic scars to sky.
    """
    out = Path(output_dir) if output_dir else DEFAULT_LOOP_RUNS_DIR / "real_sky"
    out.mkdir(parents=True, exist_ok=True)
    cache = DataCache()
    paths: list[str] = []

    for i in range(count):
        result = run_physics_loop(
            steps=steps,
            nside=nside,
            map_product_id=map_product_id,
            cache=cache,
            seed=seed + i,
            policy=ChoicePolicy.AXIS_BIASED,
            neural_prescreen_real=False,
        )
        # Rewrite steps so the supervised target is the real sky axis.
        steps_payload = []
        for s in result.steps:
            d = s.to_dict()
            d["recovered_axis"] = list(result.real_axis)
            d["true_axis"] = list(result.real_axis)
            d["axis_error_deg"] = 0.0
            steps_payload.append(d)

        run_id = f"real-{uuid.uuid4().hex[:10]}"
        payload = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "policy": "real_sky_target",
            "nside": nside,
            "seed": seed + i,
            "map_product_id": map_product_id,
            "steps": steps_payload,
            "graph_snapshot": result.graph.to_dict(),
            "extra": {
                "kind": "real_sky_finetune",
                "real_axis": result.real_axis,
                "real_score": result.real_score,
            },
            "summary": {
                "n_steps": len(steps_payload),
                "final_separation_deg": result.steps[-1].separation_deg if result.steps else None,
            },
        }
        path = out / f"{run_id}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        paths.append(str(path))

    return {
        "n_runs": len(paths),
        "output_dir": str(out),
        "map_product_id": map_product_id,
        "paths": paths,
    }


def fine_tune_on_real_sky(
    *,
    count: int = 20,
    steps: int = 3,
    nside: int = 32,
    map_product_id: str = "wmap_k_band",
    epochs: int = 80,
    seed: int = 0,
    synthetic_corpus_dir: Path | str | None = None,
    real_output_dir: Path | str | None = None,
    checkpoint_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Generate real-sky targets, merge with synthetic corpus, retrain predictors."""
    gen = generate_real_sky_training_runs(
        count=count,
        steps=steps,
        nside=nside,
        map_product_id=map_product_id,
        seed=seed,
        output_dir=real_output_dir,
    )
    # Load both corpora into one LoopCorpus
    synth = load_corpus(synthetic_corpus_dir or DEFAULT_LOOP_RUNS_DIR)
    real = load_corpus(gen["output_dir"])
    synth.samples.extend(real.samples)
    ckpt = Path(checkpoint_dir) if checkpoint_dir else DEFAULT_CHECKPOINT_DIR

    reports = {
        "generation": gen,
        "n_samples_total": synth.n_samples,
        "axis": train_axis_predictor(synth, epochs=epochs, seed=seed, checkpoint_dir=ckpt),
        "branch": train_branch_predictor(synth, epochs=epochs, seed=seed, checkpoint_dir=ckpt),
        "scar": train_scar_classifier(
            synth, epochs=max(40, epochs // 2), seed=seed, checkpoint_dir=ckpt
        ),
    }
    return reports
