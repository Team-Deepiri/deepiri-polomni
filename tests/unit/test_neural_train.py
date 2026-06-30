"""Unit tests for neural training on loop corpus."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from polomni.neural.datasets.loop_corpus import LoopCorpus, LoopSample, load_corpus
from polomni.neural.graph_node.engine import RBLEGraphEngine
from polomni.neural.train import (
    evaluate_axis_recovery,
    load_checkpoint,
    save_checkpoint,
    train_axis_predictor,
    train_branch_predictor,
)


@pytest.fixture
def synthetic_corpus(tmp_path: Path) -> LoopCorpus:
    runs = tmp_path / "loop_runs"
    runs.mkdir()
    payload = {
        "run_id": "train-run",
        "graph_snapshot": {
            "nodes": [
                {"id": 0, "mass": 8.0, "x": 0.3, "y": 0.2, "z": 0.9},
                {"id": 1, "mass": 4.0, "x": 0.1, "y": 0.1, "z": 0.98},
            ],
            "edges": [{"source": 0, "target": 1, "conductance": 1.0}],
        },
        "steps": [
            {
                "step": i,
                "true_axis": [0.2, 0.2, 0.95],
                "recovered_axis": [0.22, 0.18, 0.94],
                "detection": {
                    "metadata": {
                        "tomogram_integral": 0.2 + 0.01 * i,
                        "tomogram_bifurcation": 0.1,
                        "tomogram_contrast": 0.05,
                    }
                },
            }
            for i in range(5)
        ],
    }
    (runs / "r.json").write_text(json.dumps(payload), encoding="utf-8")
    return load_corpus(runs)


def test_train_axis_predictor_returns_history(synthetic_corpus: LoopCorpus, tmp_path: Path) -> None:
    result = train_axis_predictor(
        synthetic_corpus,
        epochs=5,
        checkpoint_dir=tmp_path / "ckpt",
    )
    assert result["trained"] is True
    assert result["epochs"] == 5
    assert len(result["loss_history"]) == 5
    assert Path(result["checkpoint"]).is_file()
    assert result["mean_axis_error_deg"] >= 0.0


def test_train_branch_predictor(synthetic_corpus: LoopCorpus, tmp_path: Path) -> None:
    result = train_branch_predictor(
        synthetic_corpus,
        epochs=5,
        checkpoint_dir=tmp_path / "ckpt",
    )
    assert result["trained"] is True
    assert "final_branch_mse" in result
    assert Path(result["checkpoint"]).is_file()


def test_evaluate_axis_recovery(synthetic_corpus: LoopCorpus) -> None:
    engine = RBLEGraphEngine(node_features=8, output_dim=3, seed=1)
    err = evaluate_axis_recovery(synthetic_corpus, engine)
    assert 0.0 <= err <= 180.0


def test_checkpoint_roundtrip(tmp_path: Path) -> None:
    engine = RBLEGraphEngine(node_features=8, output_dim=3, seed=2)
    path = save_checkpoint(engine, tmp_path / "axis_predictor", kind="axis")
    loaded = load_checkpoint(path)
    x = np.random.default_rng(0).standard_normal((2, 8))
    pred_a = engine.forward(x)
    pred_b = loaded.forward(x)
    assert pred_a.shape == pred_b.shape
    assert np.allclose(pred_a, pred_b, atol=1e-5)


def test_empty_corpus_training() -> None:
    empty = LoopCorpus()
    axis = train_axis_predictor(empty, epochs=3)
    branch = train_branch_predictor(empty, epochs=3)
    assert axis["trained"] is False
    assert branch["trained"] is False


def test_single_sample_corpus(tmp_path: Path) -> None:
    sample = LoopSample(
        run_id="solo",
        step=0,
        node_features=np.eye(2, 8),
        adjacency=np.array([[0.0, 0.6], [0.0, 0.0]]),
        true_axis=np.array([0.0, 0.0, 1.0]),
        recovered_axis=np.array([0.1, 0.0, 0.99]),
        axis_delta=np.array([0.1, 0.0, -0.01]),
        branch_weights=np.array([1.0]),
        tomogram_fingerprint=np.array([0.2, 0.1, 0.05]),
        parent_index=0,
    )
    corpus = LoopCorpus(samples=[sample])
    result = train_axis_predictor(corpus, epochs=3, checkpoint_dir=tmp_path / "ckpt")
    assert result["trained"] is True
