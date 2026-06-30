"""Unit tests for loop corpus dataset builder."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from polomni.neural.datasets.loop_corpus import (
    LoopCorpus,
    LoopSample,
    build_tensors,
    load_corpus,
)


@pytest.fixture
def synthetic_run_payload() -> dict:
    return {
        "run_id": "test-run-1",
        "policy": "axis_biased",
        "nside": 32,
        "graph_snapshot": {
            "parent_id": "0",
            "nodes": [
                {
                    "id": "0",
                    "mass": 10.0,
                    "x": 0.2,
                    "y": 0.3,
                    "z": 0.9,
                    "law_of_gravity": [6.674e-11, 1.1e-52],
                    "lambda_vacuum": 1.0e-52,
                },
                {
                    "id": "1",
                    "mass": 5.0,
                    "x": 0.1,
                    "y": 0.2,
                    "z": 0.97,
                    "law_of_gravity": [6.674e-11, 1.1e-52],
                    "lambda_vacuum": 1.0e-52,
                },
                {
                    "id": "2",
                    "mass": 4.0,
                    "x": -0.1,
                    "y": 0.15,
                    "z": 0.95,
                    "law_of_gravity": [6.674e-11, 1.1e-52],
                    "lambda_vacuum": 1.0e-52,
                },
            ],
            "edges": [
                {"source": "0", "target": "1", "conductance": 0.7},
                {"source": "0", "target": "2", "conductance": 0.3},
            ],
        },
        "steps": [
            {
                "step": 0,
                "true_axis": [0.1, 0.2, 0.97],
                "recovered_axis": [0.12, 0.19, 0.96],
                "axis_error_deg": 2.5,
                "rble_score": 0.42,
                "detection": {
                    "metadata": {
                        "tomogram_integral": 0.31,
                        "tomogram_bifurcation": 0.18,
                        "tomogram_contrast": 0.09,
                    }
                },
            },
            {
                "step": 1,
                "true_axis": [0.11, 0.21, 0.96],
                "recovered_axis": [0.13, 0.20, 0.95],
                "axis_error_deg": 1.8,
                "rble_score": 0.38,
                "tomogram_integral": 0.28,
                "tomogram_bifurcation": 0.15,
                "tomogram_contrast": 0.11,
            },
        ],
    }


@pytest.fixture
def corpus_dir(tmp_path: Path, synthetic_run_payload: dict) -> Path:
    runs = tmp_path / "loop_runs"
    runs.mkdir()
    (runs / "run_a.json").write_text(json.dumps(synthetic_run_payload), encoding="utf-8")
    payload_b = dict(synthetic_run_payload)
    payload_b["run_id"] = "test-run-2"
    (runs / "run_b.json").write_text(json.dumps(payload_b), encoding="utf-8")
    return runs


def test_load_corpus_builds_samples(corpus_dir: Path) -> None:
    corpus = load_corpus(corpus_dir)
    assert corpus.n_samples == 4
    assert corpus.summary()["n_runs"] == 2
    sample = corpus.samples[0]
    assert sample.node_features.shape == (3, 8)
    assert sample.adjacency.shape == (3, 3)
    assert sample.tomogram_fingerprint.shape == (3,)
    assert sample.branch_weights.size == 2
    assert np.isclose(sample.branch_weights.sum(), 1.0)


def test_axis_delta_and_parent_index(corpus_dir: Path) -> None:
    corpus = load_corpus(corpus_dir)
    sample = corpus.samples[0]
    expected_delta = sample.recovered_axis - sample.true_axis
    assert np.allclose(sample.axis_delta, expected_delta)
    assert sample.parent_index == 0


def test_build_tensors_pads_graphs(corpus_dir: Path) -> None:
    corpus = load_corpus(corpus_dir)
    tensors = build_tensors(corpus)
    assert tensors["node_features"].shape[0] == 4
    assert tensors["node_features"].shape[1] == 3
    assert tensors["node_features"].shape[2] == 8
    assert tensors["recovered_axis"].shape == (4, 3)
    assert tensors["branch_weights"].shape == (4, 2)
    assert np.all(tensors["node_mask"][:, :3] == 1.0)


def test_empty_corpus_tensors() -> None:
    tensors = build_tensors(LoopCorpus())
    assert tensors["node_features"].shape[0] == 0


def test_manual_loop_sample() -> None:
    sample = LoopSample(
        run_id="x",
        step=0,
        node_features=np.ones((1, 8)),
        adjacency=np.zeros((1, 1)),
        true_axis=np.array([0.0, 0.0, 1.0]),
        recovered_axis=np.array([0.1, 0.0, 0.99]),
        axis_delta=np.array([0.1, 0.0, -0.01]),
        branch_weights=np.array([1.0]),
        tomogram_fingerprint=np.array([0.1, 0.2, 0.3]),
    )
    corpus = LoopCorpus(samples=[sample])
    assert corpus.max_nodes == 1
    assert corpus.max_branches == 1
