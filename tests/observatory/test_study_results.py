"""Tests for sealed, mode-aware P1 result publication."""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from polomni.observatory.studies import results
from polomni.observatory.studies.results import (
    AmbiguousCanonicalResultError,
    InvalidResultPathError,
    ResultConflictError,
    load_canonical_blind_result,
    load_result,
    publish_result,
    resolve_result_path,
)


def _payload(mode: str, blind: bool, *, writer: int = 0) -> dict:
    return {
        "study_id": "p1_cmb_radon_scar",
        "config_version": "1.0.0",
        "ran_at": "2026-08-16T12:00:00+00:00",
        "git_sha": "eee86c9",
        "mode": mode,
        "blind": blind,
        "map_product_id": "planck_smica_cmb" if blind else "wmap_k_band",
        "writer": writer,
    }


def test_default_paths_are_mode_specific(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    assert resolve_result_path("holdout_blind").name == "RESULT.json"
    assert resolve_result_path("calibration").name == "CALIBRATION_RESULT.json"
    assert resolve_result_path("exploratory").name == "EXPLORATORY_RESULT.json"


@pytest.mark.parametrize("mode", ["calibration", "exploratory"])
def test_non_blind_modes_cannot_target_canonical_result(
    monkeypatch,
    tmp_path: Path,
    mode: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    blind = publish_result(_payload("holdout_blind", True), mode="holdout_blind")
    before = Path(blind["result_path"]).read_bytes()

    with pytest.raises(InvalidResultPathError):
        publish_result(
            _payload(mode, False),
            mode=mode,  # type: ignore[arg-type]
            output_path=results.CANONICAL_BLIND_RESULT,
        )

    assert Path(blind["result_path"]).read_bytes() == before


def test_canonical_blind_result_is_sealed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    first = publish_result(_payload("holdout_blind", True), mode="holdout_blind")

    with pytest.raises(ResultConflictError, match="sealed"):
        publish_result(_payload("holdout_blind", True, writer=2), mode="holdout_blind")

    persisted = json.loads(Path(first["result_path"]).read_text(encoding="utf-8"))
    assert persisted == first
    assert persisted["writer"] == 0


def test_explicit_alternate_blind_path_is_allowed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    alternate = tmp_path / "replication" / "RERUN_RESULT.json"

    result = publish_result(
        _payload("holdout_blind", True),
        mode="holdout_blind",
        output_path=alternate,
        artifact_role="replication_rerun",
    )

    assert Path(result["result_path"]) == alternate
    assert result["artifact_role"] == "replication_rerun"
    assert not results.CANONICAL_BLIND_RESULT.exists()


def test_concurrent_canonical_writers_have_one_winner(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    barrier = threading.Barrier(2)

    def attempt(writer: int) -> str:
        barrier.wait(timeout=5)
        try:
            publish_result(
                _payload("holdout_blind", True, writer=writer),
                mode="holdout_blind",
            )
        except ResultConflictError:
            return "conflict"
        return "published"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, (1, 2)))

    assert sorted(outcomes) == ["conflict", "published"]
    persisted = json.loads(results.CANONICAL_BLIND_RESULT.read_text(encoding="utf-8"))
    assert persisted["writer"] in {1, 2}
    assert list(results.RESULTS_DIR.glob(".RESULT.json.*.tmp")) == []


def test_atomic_failure_preserves_previous_result(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    first = publish_result(_payload("calibration", False), mode="calibration")
    path = Path(first["result_path"])
    before = path.read_bytes()

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("injected publication failure")

    monkeypatch.setattr(results, "atomic_replace", fail_replace)
    with pytest.raises(OSError, match="injected"):
        publish_result(_payload("calibration", False, writer=2), mode="calibration")

    assert path.read_bytes() == before
    assert load_result(path) == first
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []


def test_returned_and_persisted_payloads_match(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    returned = publish_result(_payload("exploratory", False), mode="exploratory")

    persisted = json.loads(Path(returned["result_path"]).read_text(encoding="utf-8"))
    assert persisted == returned


def test_ambiguous_historical_canonical_result_is_rejected(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    canonical = results.CANONICAL_BLIND_RESULT
    canonical.parent.mkdir(parents=True)
    canonical.write_text(
        json.dumps({"mode": "calibration", "blind": False}),
        encoding="utf-8",
    )

    with pytest.raises(AmbiguousCanonicalResultError, match="operator action"):
        load_canonical_blind_result()
    with pytest.raises(AmbiguousCanonicalResultError, match="operator action"):
        load_result(canonical)
    with pytest.raises(AmbiguousCanonicalResultError, match="operator action"):
        publish_result(_payload("holdout_blind", True), mode="holdout_blind")

    assert json.loads(canonical.read_text(encoding="utf-8"))["mode"] == "calibration"


def test_valid_legacy_blind_result_is_accepted(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    canonical = results.CANONICAL_BLIND_RESULT
    canonical.parent.mkdir(parents=True)
    legacy = _payload("holdout_blind", True)
    canonical.write_text(json.dumps(legacy), encoding="utf-8")

    assert load_canonical_blind_result() == legacy
    assert load_result(canonical) == legacy


def test_malformed_historical_canonical_result_is_rejected(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    canonical = results.CANONICAL_BLIND_RESULT
    canonical.parent.mkdir(parents=True)
    malformed = b'{"mode": "holdout_blind"'
    canonical.write_bytes(malformed)

    with pytest.raises(AmbiguousCanonicalResultError, match="unreadable or invalid"):
        load_canonical_blind_result()
    with pytest.raises(AmbiguousCanonicalResultError, match="unreadable or invalid"):
        publish_result(_payload("holdout_blind", True), mode="holdout_blind")

    assert canonical.read_bytes() == malformed


def test_incomplete_historical_canonical_metadata_is_ambiguous(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    canonical = results.CANONICAL_BLIND_RESULT
    canonical.parent.mkdir(parents=True)
    canonical.write_text(json.dumps({"blind": True}), encoding="utf-8")

    with pytest.raises(AmbiguousCanonicalResultError, match="operator action"):
        load_canonical_blind_result()
