"""Append-only event log for pipeline ingest and scoring steps."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from polomni.observatory.pipeline.config import get_settings


@dataclass(slots=True)
class PipelineEvent:
    """Single pipeline lifecycle event."""

    timestamp: datetime
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)


class EventLog:
    """JSONL event log under ``<cache>/events.jsonl``."""

    def __init__(self, path: Path | None = None) -> None:
        if path is None:
            path = get_settings().data_cache / "events.jsonl"
        self.path = path.resolve()

    def append(self, event: PipelineEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": event.timestamp.isoformat(),
            "kind": event.kind,
            "payload": event.payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")

    def read_all(self) -> list[PipelineEvent]:
        if not self.path.exists():
            return []
        events: list[PipelineEvent] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            events.append(
                PipelineEvent(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    kind=row["kind"],
                    payload=row.get("payload", {}),
                )
            )
        return events


def pipeline_event(kind: str, **payload: Any) -> PipelineEvent:
    """Convenience constructor with UTC timestamp."""
    return PipelineEvent(
        timestamp=datetime.now(timezone.utc),
        kind=kind,
        payload=payload,
    )
