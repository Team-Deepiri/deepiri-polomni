"""Locked, atomic persistence for P1 study result artifacts."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Literal

from filelock import FileLock

from polomni.observatory.pipeline.filesystem import atomic_replace, sync_directory

StudyMode = Literal["holdout_blind", "calibration", "exploratory"]

RESULTS_DIR = Path("data/studies/p1_holdout")
CANONICAL_BLIND_RESULT = RESULTS_DIR / "RESULT.json"
CALIBRATION_RESULT = RESULTS_DIR / "CALIBRATION_RESULT.json"
EXPLORATORY_RESULT = RESULTS_DIR / "EXPLORATORY_RESULT.json"
REPLICATION_RESULT = RESULTS_DIR / "replication" / "RERUN_RESULT.json"


class ResultStoreError(RuntimeError):
    """Base error for P1 result publication failures."""


class ResultConflictError(ResultStoreError):
    """Raised when a sealed canonical blind result would be replaced."""


class AmbiguousCanonicalResultError(ResultStoreError):
    """Raised when historical canonical metadata cannot prove a blind run."""


class InvalidResultPathError(ResultStoreError):
    """Raised when a non-blind run targets the canonical blind path."""


def _absolute(path: Path) -> Path:
    return path if path.is_absolute() else Path.cwd() / path


def _same_path(left: Path, right: Path) -> bool:
    return _absolute(left).resolve() == _absolute(right).resolve()


def is_canonical_blind_path(path: Path) -> bool:
    """Return whether *path* addresses the reserved canonical blind artifact."""
    return _same_path(path, CANONICAL_BLIND_RESULT)


def resolve_result_path(
    mode: StudyMode,
    output_path: Path | None = None,
) -> Path:
    """Resolve an explicit path or the deterministic path for *mode*."""
    if output_path is not None:
        path = Path(output_path)
    elif mode == "holdout_blind":
        path = CANONICAL_BLIND_RESULT
    elif mode == "calibration":
        path = CALIBRATION_RESULT
    else:
        path = EXPLORATORY_RESULT

    if mode != "holdout_blind" and is_canonical_blind_path(path):
        raise InvalidResultPathError(
            "Calibration and exploratory runs cannot target the canonical blind result"
        )
    return path


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AmbiguousCanonicalResultError(
            "Canonical RESULT.json is unreadable or invalid; operator action is required"
        ) from exc
    if not isinstance(payload, dict):
        raise AmbiguousCanonicalResultError(
            "Canonical RESULT.json is not a JSON object; operator action is required"
        )
    return payload


def _validate_blind_payload(payload: dict[str, Any]) -> None:
    if payload.get("mode") != "holdout_blind" or payload.get("blind") is not True:
        raise AmbiguousCanonicalResultError(
            "Canonical RESULT.json is not unambiguously identified as a blind holdout; "
            "operator action is required"
        )


@contextmanager
def _publication_lock(directory: Path) -> Iterator[None]:
    directory.mkdir(parents=True, exist_ok=True)
    lock = FileLock(
        directory / ".p1-results.lock",
        timeout=30,
        preserve_lock_file=True,
    )
    with lock:
        yield


def check_canonical_blind_available(path: Path | None = None) -> None:
    """Fail early if the canonical blind result is sealed or ambiguous.

    Publication repeats this check while holding the same lock, so this
    preflight is only an optimization that avoids needless study computation.
    """
    destination = path or CANONICAL_BLIND_RESULT
    destination = _absolute(destination)
    with _publication_lock(destination.parent):
        if not destination.exists():
            return
        payload = _read_json_object(destination)
        _validate_blind_payload(payload)
        raise ResultConflictError(
            "The canonical blind result is sealed; select an explicit alternate output path"
        )


def load_result(path: Path) -> dict[str, Any] | None:
    """Load a non-canonical result, returning ``None`` when absent."""
    path = _absolute(path)
    if is_canonical_blind_path(path):
        return load_canonical_blind_result(path)
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Study result is not a JSON object: {path}")
    return payload


def load_canonical_blind_result(path: Path | None = None) -> dict[str, Any] | None:
    """Load and validate the canonical blind artifact without guessing."""
    destination = _absolute(path or CANONICAL_BLIND_RESULT)
    if not destination.is_file():
        return None
    payload = _read_json_object(destination)
    _validate_blind_payload(payload)
    return payload


def publish_result(
    payload: dict[str, Any],
    *,
    mode: StudyMode,
    output_path: Path | None = None,
    artifact_role: str | None = None,
) -> dict[str, Any]:
    """Publish one fully serialized P1 result and return the persisted payload."""
    destination = _absolute(resolve_result_path(mode, output_path))
    canonical = is_canonical_blind_path(destination)
    if canonical:
        _validate_blind_payload(payload)

    document = dict(payload)
    document["result_path"] = str(destination.resolve())
    if canonical:
        default_role = "canonical_blind"
    elif mode == "holdout_blind":
        default_role = "alternate_blind"
    else:
        default_role = mode
    document["artifact_role"] = artifact_role or default_role
    serialized = json.dumps(document, indent=2) + "\n"

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())

        with _publication_lock(destination.parent):
            if canonical and destination.exists():
                existing = _read_json_object(destination)
                _validate_blind_payload(existing)
                raise ResultConflictError(
                    "The canonical blind result is sealed; select an explicit alternate "
                    "output path"
                )
            atomic_replace(temporary, destination)
            temporary = None
            sync_directory(destination.parent)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    return document
