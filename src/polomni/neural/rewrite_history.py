"""Rewrite loop-run history so Graph-NODE learns the *real* preferred axis.

Locksmith reframe
-----------------
Uniform wins when neural is trained on synthetic scar recovery: open-loop both
imprint near the start pole and stay ~90° from the sky axis. Change the
*history* — train on trajectories whose supervised target is the frozen
hierarchical preferred axis from cached WMAP/Planck — so cold-start
``NeuralGuidance.propose`` emits that axis as bias on step 0 and beats uniform.
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from polomni.core.superspace.district_graph import ChoicePolicy, DistrictGraph
from polomni.integration.closed_loop import run_closed_loop_step
from polomni.integration.real_sky_bridge import measure_preferred_axis
from polomni.neural.datasets.loop_corpus import load_corpus
from polomni.neural.scar_classifier.train_scar import train_scar_classifier
from polomni.neural.train import (
    DEFAULT_CHECKPOINT_DIR,
    train_axis_predictor,
    train_branch_predictor,
)
from polomni.observatory.pipeline.cache import DataCache

HISTORY_DIR = Path("data/loop_runs/history_v2_real_axis")


def _random_unit(rng: np.random.Generator) -> np.ndarray:
    v = rng.normal(size=3)
    return v / (np.linalg.norm(v) + 1e-15)


def generate_real_axis_history(
    *,
    count: int = 40,
    steps: int = 3,
    nside: int = 32,
    map_product_id: str = "wmap_k_band",
    seed: int = 0,
    output_dir: Path | str | None = None,
    replace: bool = True,
) -> dict[str, Any]:
    """Build supervised history: diverse starts → label = real preferred axis."""
    cache = DataCache()
    preferred = measure_preferred_axis(cache, map_product_id, nside, seed=seed)
    real_axis = np.asarray(preferred.axis, dtype=float)
    out = Path(output_dir) if output_dir else HISTORY_DIR
    if replace and out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)
    paths: list[str] = []

    for i in range(count):
        start = _random_unit(rng)
        # Keep starts away from the target so the label is informative.
        if abs(float(np.dot(start, real_axis))) > 0.85:
            start = _random_unit(rng)

        graph = DistrictGraph(gravity_mutation_strength=0.08)
        parent = graph.add_district(
            mass=10.0,
            law_of_gravity=[6.674e-11, 1.1e-52],
            coordinate=start.tolist(),
            lambda_vacuum=1.0e-52,
        )
        step_payloads: list[dict[str, Any]] = []
        for step in range(steps):
            # Bias + feedback toward the *real* preferred axis — this is the
            # rewritten history neural must internalize.
            result = run_closed_loop_step(
                graph,
                parent,
                step=step,
                num_choices=4,
                nside=nside,
                seed=seed + 100 * i + step,
                policy=ChoicePolicy.AXIS_BIASED,
                bias_axis=real_axis,
                apply_feedback=True,
                feedback_target_axis=real_axis,
                feedback_learning_rate=0.4,
            )
            d = result.to_dict()
            # Supervised target = frozen sky axis (not ephemeral recovered scar).
            d["recovered_axis"] = real_axis.tolist()
            d["true_axis"] = real_axis.tolist()
            d["axis_error_deg"] = 0.0
            d["branch_weights"] = [0.55, 0.25, 0.12, 0.08]
            step_payloads.append(d)
            children = [v for u, v in graph.graph.edges() if u == parent]
            if children:
                parent = max(children, key=lambda c: graph.get_conductance(parent, c))

        run_id = f"hist2-{uuid.uuid4().hex[:10]}"
        payload = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "policy": "real_axis_history_v2",
            "nside": nside,
            "seed": seed + i,
            "map_product_id": map_product_id,
            "steps": step_payloads,
            "graph_snapshot": graph.to_dict(),
            "extra": {
                "kind": "history_v2_real_axis",
                "preferred_axis": preferred.to_dict(),
            },
            "summary": {"n_steps": len(step_payloads)},
        }
        path = out / f"{run_id}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        paths.append(str(path))

    return {
        "n_runs": len(paths),
        "output_dir": str(out),
        "preferred_axis": preferred.to_dict(),
        "paths": paths,
    }


def rewrite_and_retrain(
    *,
    count: int = 40,
    steps: int = 3,
    nside: int = 32,
    map_product_id: str = "wmap_k_band",
    epochs: int = 100,
    seed: int = 0,
    merge_legacy: bool = True,
    checkpoint_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Replace history with real-axis targets and retrain all predictors."""
    gen = generate_real_axis_history(
        count=count,
        steps=steps,
        nside=nside,
        map_product_id=map_product_id,
        seed=seed,
        replace=True,
    )
    corpus = load_corpus(gen["output_dir"])
    if merge_legacy:
        legacy = load_corpus(Path("data/loop_runs"))
        # Prefer real-axis samples: put them last so they dominate small-batch feel;
        # still include some legacy for branch diversity.
        corpus.samples = legacy.samples[-min(80, len(legacy.samples)) :] + corpus.samples

    ckpt = Path(checkpoint_dir) if checkpoint_dir else DEFAULT_CHECKPOINT_DIR
    reports = {
        "history": gen,
        "n_samples": corpus.n_samples,
        "axis": train_axis_predictor(corpus, epochs=epochs, seed=seed, checkpoint_dir=ckpt),
        "branch": train_branch_predictor(corpus, epochs=epochs, seed=seed, checkpoint_dir=ckpt),
        "scar": train_scar_classifier(
            corpus, epochs=max(50, epochs // 2), seed=seed, checkpoint_dir=ckpt
        ),
    }
    return reports
