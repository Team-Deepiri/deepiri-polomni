"""Tests for batch simulation."""

from polomni.core.simulation.batch import run_batch_simulation


def test_run_batch_simulation() -> None:
    results = run_batch_simulation([1, 2, 3], choices=3, districts=1)
    assert len(results) == 3
    assert all(r["packets_spawned"] > 0 for r in results)
    assert results[0]["seed"] == 1
