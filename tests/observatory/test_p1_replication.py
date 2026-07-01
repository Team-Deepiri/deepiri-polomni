"""Tests for Gate 5 independent replication."""

from pathlib import Path

from polomni.observatory.studies.gates import check_gate5_replication
from polomni.observatory.studies.replication import (
    compare_holdout_to_golden,
    load_golden_reference,
    verify_cache_checksums,
)


def test_golden_reference_file_exists() -> None:
    p = Path("data/studies/p1_holdout/golden_holdout_v1.json")
    assert p.is_file()
    golden = load_golden_reference()
    assert golden["expected_holdout"]["blind"] is True


def test_cache_checksums_when_cached() -> None:
    from polomni.math.proofs.real_data import cache_ready

    if not cache_ready():
        return
    ok, errors = verify_cache_checksums()
    assert ok, errors


def test_holdout_matches_golden_when_result_present() -> None:
    from polomni.math.proofs.real_data import cache_ready
    from polomni.observatory.studies.gates import load_latest_result

    if not cache_ready():
        return
    result = load_latest_result()
    if result is None or not result.get("blind"):
        return
    ok, errors = compare_holdout_to_golden(result)
    assert ok, errors


def test_gate5_check_when_cached() -> None:
    from polomni.math.proofs.real_data import cache_ready
    from polomni.observatory.studies.gates import load_latest_result

    if not cache_ready() or load_latest_result() is None:
        return
    check = check_gate5_replication(rerun=False)
    assert check.gate == "G5"
    assert check.passed
