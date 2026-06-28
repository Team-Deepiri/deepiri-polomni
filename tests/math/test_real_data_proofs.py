"""Integration tests for real-data verification proofs."""

import pytest

from polomni.math.proofs.convergence import prove_all_convergence
from polomni.math.proofs.real_data import prove_all_real_data
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.processor import ingest_standard_data


@pytest.mark.integration
@pytest.mark.observatory
def test_real_data_proofs_with_fetched_cache(tmp_path) -> None:
    cache = DataCache(tmp_path)
    ingest_standard_data(cache, include_heavy=False, force=True, fetch_gw=True)
    results = prove_all_real_data(cache, target_nside=64)
    assert len(results) >= 6
    passed = [r for r in results if r.passed]
    assert len(passed) >= 4, [(r.id, r.message) for r in results if not r.passed]


def test_convergence_proofs_pass() -> None:
    results = prove_all_convergence()
    assert all(r.passed for r in results)
