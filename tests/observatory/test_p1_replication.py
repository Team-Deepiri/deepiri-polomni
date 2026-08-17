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


def test_replication_rerun_does_not_replace_canonical(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from polomni.observatory.pipeline.cache import DataCache
    from polomni.observatory.studies import replication
    from polomni.observatory.studies.results import (
        REPLICATION_RESULT,
        publish_result,
    )

    monkeypatch.chdir(tmp_path)
    canonical = publish_result(
        {
            "mode": "holdout_blind",
            "blind": True,
            "map_product_id": "planck_smica_cmb",
            "detection": {"rble_score": 1.0, "preferred_axis": [0.0, 0.0, 1.0]},
            "p1_supported": False,
            "p1_falsified": True,
        },
        mode="holdout_blind",
    )
    canonical_path = Path(canonical["result_path"])
    before = canonical_path.read_bytes()
    captured: dict = {}

    def fake_run_p1_study(**kwargs):
        captured.update(kwargs)
        return publish_result(
            {
                "mode": "holdout_blind",
                "blind": True,
                "map_product_id": "planck_smica_cmb",
                "detection": {
                    "rble_score": 1.0,
                    "preferred_axis": [0.0, 0.0, 1.0],
                },
                "p1_supported": False,
                "p1_falsified": True,
            },
            mode="holdout_blind",
            output_path=kwargs["output_path"],
            artifact_role=kwargs["artifact_role"],
        )

    monkeypatch.setattr(replication, "run_p1_study", fake_run_p1_study)
    monkeypatch.setattr(
        replication,
        "load_golden_reference",
        lambda path=None: {"version": "1", "expected_holdout": {"rble_score": 1.0}},
    )
    monkeypatch.setattr(
        replication,
        "verify_cache_checksums",
        lambda golden, cache=None: (True, []),
    )
    monkeypatch.setattr(
        replication,
        "compare_holdout_to_golden",
        lambda result, golden: (True, []),
    )

    report = replication.run_independent_replication(
        rerun=True,
        cache=DataCache(tmp_path / "cache"),
    )

    assert Path(captured["output_path"]) == REPLICATION_RESULT
    assert captured["artifact_role"] == "replication_rerun"
    assert Path(report["source_result_path"]).name == "RERUN_RESULT.json"
    assert canonical_path.read_bytes() == before


def test_replication_rejects_canonical_output(monkeypatch, tmp_path: Path) -> None:
    import pytest

    from polomni.observatory.studies.replication import run_independent_replication
    from polomni.observatory.studies.results import (
        CANONICAL_BLIND_RESULT,
        InvalidResultPathError,
    )

    monkeypatch.chdir(tmp_path)

    with pytest.raises(InvalidResultPathError, match="cannot target"):
        run_independent_replication(
            rerun=True,
            output_path=CANONICAL_BLIND_RESULT,
        )


def test_replication_identifies_legacy_canonical_source(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import json

    from polomni.observatory.pipeline.cache import DataCache
    from polomni.observatory.studies import replication
    from polomni.observatory.studies.results import CANONICAL_BLIND_RESULT

    monkeypatch.chdir(tmp_path)
    CANONICAL_BLIND_RESULT.parent.mkdir(parents=True)
    CANONICAL_BLIND_RESULT.write_text(
        json.dumps(
            {
                "mode": "holdout_blind",
                "blind": True,
                "map_product_id": "planck_smica_cmb",
                "detection": {
                    "rble_score": 1.0,
                    "preferred_axis": [0.0, 0.0, 1.0],
                },
                "p1_supported": False,
                "p1_falsified": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        replication,
        "load_golden_reference",
        lambda path=None: {"version": "1", "expected_holdout": {"rble_score": 1.0}},
    )
    monkeypatch.setattr(
        replication,
        "verify_cache_checksums",
        lambda golden, cache=None: (True, []),
    )
    monkeypatch.setattr(
        replication,
        "compare_holdout_to_golden",
        lambda result, golden: (True, []),
    )

    report = replication.run_independent_replication(
        cache=DataCache(tmp_path / "cache"),
    )

    assert report["rerun"] is False
    assert report["source_result_path"] == str(CANONICAL_BLIND_RESULT.resolve())
