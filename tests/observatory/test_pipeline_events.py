"""Tests for pipeline event log."""

import json
from datetime import datetime, timezone
from pathlib import Path

from polomni.observatory.pipeline.events import EventLog, PipelineEvent


def test_event_log_append_and_read(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    log = EventLog(log_path)

    event = PipelineEvent(
        timestamp=datetime(2026, 6, 28, 12, 0, tzinfo=timezone.utc),
        kind="ingest_start",
        payload={"product_ids": ["planck_cmb_tt_power"]},
    )
    log.append(event)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["kind"] == "ingest_start"
    assert row["payload"]["product_ids"] == ["planck_cmb_tt_power"]

    events = log.read_all()
    assert len(events) == 1
    assert events[0].kind == "ingest_start"


def test_event_log_creates_parent_dir(tmp_path: Path) -> None:
    log_path = tmp_path / "nested" / "events.jsonl"
    log = EventLog(log_path)
    log.append(
        PipelineEvent(
            timestamp=datetime.now(timezone.utc),
            kind="test",
            payload={},
        )
    )
    assert log_path.exists()
