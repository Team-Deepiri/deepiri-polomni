"""Tests for Graph-NODE guidance + scar classifier training."""

from __future__ import annotations

from pathlib import Path

from polomni.core.superspace.district_graph import ChoicePolicy, DistrictGraph
from polomni.integration.closed_loop import run_closed_loop
from polomni.neural.datasets.loop_corpus import LoopCorpus, LoopSample
from polomni.neural.guidance import NeuralGuidance
from polomni.neural.scar_classifier.train_scar import train_scar_classifier
from polomni.neural.train import train_axis_predictor, train_branch_predictor
import numpy as np


def _tiny_corpus(n: int = 6) -> LoopCorpus:
    samples = []
    for i in range(n):
        axis = np.array([0.0, 0.0, 1.0], dtype=float)
        feat = np.zeros((2, 8), dtype=float)
        feat[0, 0] = 1.0
        feat[0, 4:7] = [0.1, 0.2, 0.9]
        feat[0, 7] = 1.0
        feat[1] = feat[0] * 1.01
        adj = np.array([[0.0, 0.6], [0.6, 0.0]], dtype=float)
        recovered = axis + np.array([0.05 * i, 0.0, 0.0])
        recovered = recovered / np.linalg.norm(recovered)
        samples.append(
            LoopSample(
                run_id=f"t{i}",
                step=0,
                node_features=feat,
                adjacency=adj,
                true_axis=axis,
                recovered_axis=recovered,
                axis_delta=recovered - axis,
                branch_weights=np.array([0.7, 0.3], dtype=float),
                tomogram_fingerprint=np.array([1.0 + 0.1 * i, 0.5, 0.2], dtype=float),
                parent_index=0,
            )
        )
    return LoopCorpus(samples=samples)


def test_neural_guidance_fallback(tmp_path: Path):
    g = NeuralGuidance(checkpoint_dir=tmp_path)
    assert not g.ready
    graph = DistrictGraph()
    pid = graph.add_district(
        mass=1.0,
        law_of_gravity=[1.0, 0.0],
        coordinate=[0.0, 0.0, 1.0],
        lambda_vacuum=1e-52,
    )
    prop = g.propose(graph, pid, num_choices=4, last_recovered_axis=[1.0, 0.0, 0.0])
    assert prop["policy"] == ChoicePolicy.AXIS_BIASED
    assert prop["source"] == "fallback_axis_biased"


def test_train_and_guide(tmp_path: Path):
    corpus = _tiny_corpus()
    axis = train_axis_predictor(corpus, epochs=5, checkpoint_dir=tmp_path, seed=1)
    branch = train_branch_predictor(corpus, epochs=5, checkpoint_dir=tmp_path, seed=1)
    scar = train_scar_classifier(corpus, epochs=5, checkpoint_dir=tmp_path, seed=1)
    assert axis["trained"] and branch["trained"] and scar["trained"]

    g = NeuralGuidance(checkpoint_dir=tmp_path)
    assert g.ready
    graph = DistrictGraph()
    pid = graph.add_district(
        mass=1.0,
        law_of_gravity=[1.0, 0.0],
        coordinate=[0.2, 0.3, 0.9],
        lambda_vacuum=1e-52,
    )
    prop = g.propose(graph, pid, num_choices=4)
    assert prop["policy"] == ChoicePolicy.NEURAL
    assert prop["source"] == "graph_node"


def test_closed_loop_neural_policy_runs():
    _, results = run_closed_loop(
        steps=2, num_choices=3, nside=16, seed=2, policy=ChoicePolicy.NEURAL
    )
    assert len(results) == 2
    assert results[-1].axis_error_deg >= 0.0
