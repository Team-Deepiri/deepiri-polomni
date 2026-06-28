"""Local cache for fetched cosmology data products."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from polomni.observatory.pipeline.config import get_settings


def default_cache_dir() -> Path:
    return get_settings().data_cache


class CacheEntry(BaseModel):
    product_id: str
    path: str
    url: str
    fetched_at: datetime
    size_bytes: int
    etag: str | None = None
    content_sha256: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class CacheManifest(BaseModel):
    version: int = 1
    entries: dict[str, CacheEntry] = Field(default_factory=dict)


class DataCache:
    """Filesystem cache with JSON manifest under ``<root>/manifest.json``."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_cache_dir()).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self.root / "manifest.json"

    def path_for(self, product_id: str, filename: str) -> Path:
        return self.root / product_id / filename

    def load_manifest(self) -> CacheManifest:
        if not self._manifest_path.exists():
            return CacheManifest()
        return CacheManifest.model_validate_json(self._manifest_path.read_text())

    def save_manifest(self, manifest: CacheManifest) -> None:
        self._manifest_path.write_text(manifest.model_dump_json(indent=2))

    def get_entry(self, product_id: str) -> CacheEntry | None:
        return self.load_manifest().entries.get(product_id)

    def is_fresh(self, product_id: str, max_age_hours: float) -> bool:
        entry = self.get_entry(product_id)
        if entry is None:
            return False
        path = Path(entry.path)
        if not path.exists():
            return False
        age_h = (datetime.now(timezone.utc) - entry.fetched_at).total_seconds() / 3600.0
        return age_h < max_age_hours

    def record(
        self,
        product_id: str,
        path: Path,
        url: str,
        *,
        etag: str | None = None,
        content_sha256: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> CacheEntry:
        manifest = self.load_manifest()
        entry = CacheEntry(
            product_id=product_id,
            path=str(path.resolve()),
            url=url,
            fetched_at=datetime.now(timezone.utc),
            size_bytes=path.stat().st_size,
            etag=etag,
            content_sha256=content_sha256,
            extra=extra or {},
        )
        manifest.entries[product_id] = entry
        self.save_manifest(manifest)
        return entry

    def resolved_path(self, product_id: str) -> Path | None:
        entry = self.get_entry(product_id)
        if entry is None:
            return None
        p = Path(entry.path)
        return p if p.exists() else None
