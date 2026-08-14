"""Local cache for fetched cosmology data products."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import secrets
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

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
    last_modified: str | None = None
    content_sha256: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class CacheManifest(BaseModel):
    version: int = 1
    entries: dict[str, CacheEntry] = Field(default_factory=dict)


def _fsync_directory(path: Path) -> None:
    """Persist directory-entry changes after an atomic replacement."""
    fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write_text(path: Path, text: str) -> None:
    """Durably replace *path* with fully written UTF-8 text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        _fsync_directory(path.parent)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class DataCache:
    """Filesystem cache with JSON manifest under ``<root>/manifest.json``."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_cache_dir()).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self.root / "manifest.json"
        self._manifest_lock_path = self.root / ".manifest.lock"

    def path_for(self, product_id: str, filename: str) -> Path:
        return self.root / product_id / filename

    def load_manifest(self) -> CacheManifest:
        if not self._manifest_path.exists():
            return CacheManifest()
        return CacheManifest.model_validate_json(self._manifest_path.read_text(encoding="utf-8"))

    @contextmanager
    def _manifest_lock(self) -> Iterator[None]:
        """Exclusively lock shared cache metadata for a short transaction."""
        with self._manifest_lock_path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _save_manifest_unlocked(self, manifest: CacheManifest) -> None:
        _atomic_write_text(self._manifest_path, manifest.model_dump_json(indent=2))

    def save_manifest(self, manifest: CacheManifest) -> None:
        with self._manifest_lock():
            self._save_manifest_unlocked(manifest)

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
        last_modified: str | None = None,
        content_sha256: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> CacheEntry:
        entry = CacheEntry(
            product_id=product_id,
            path=str(path.resolve()),
            url=url,
            fetched_at=datetime.now(timezone.utc),
            size_bytes=path.stat().st_size,
            etag=etag,
            last_modified=last_modified,
            content_sha256=content_sha256,
            extra=extra or {},
        )
        with self._manifest_lock():
            manifest = self.load_manifest()
            manifest.entries[product_id] = entry
            self._save_manifest_unlocked(manifest)
        return entry

    def refresh_entry(self, product_id: str) -> CacheEntry:
        """Refresh freshness without changing stored object metadata."""
        with self._manifest_lock():
            manifest = self.load_manifest()
            entry = manifest.entries.get(product_id)
            if entry is None:
                raise KeyError(f"Cached product not found: {product_id!r}")
            refreshed = entry.model_copy(update={"fetched_at": datetime.now(timezone.utc)})
            manifest.entries[product_id] = refreshed
            self._save_manifest_unlocked(manifest)
        return refreshed

    def install_temp_file(
        self,
        product_id: str,
        temporary: Path,
        destination: Path,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        content_sha256: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> CacheEntry:
        """Atomically install a completed temporary artifact and record it."""
        temporary = temporary.resolve()
        destination = destination.resolve()
        if temporary.parent != destination.parent:
            raise ValueError("Temporary cache artifacts must share the destination directory")

        with self._manifest_lock():
            manifest = self.load_manifest()
            destination_existed = destination.exists()
            backup: Path | None = None
            backup_created = False
            installed = False
            rollback_restored = False
            transaction_succeeded = False
            try:
                if destination_existed:
                    candidate = destination.with_name(
                        f".{destination.name}.{secrets.token_hex(8)}.bak"
                    )
                    os.link(destination, candidate)
                    backup = candidate
                    backup_created = True
                os.replace(temporary, destination)
                installed = True
                _fsync_directory(destination.parent)
                entry = CacheEntry(
                    product_id=product_id,
                    path=str(destination),
                    url=url,
                    fetched_at=datetime.now(timezone.utc),
                    size_bytes=destination.stat().st_size,
                    etag=etag,
                    last_modified=last_modified,
                    content_sha256=content_sha256,
                    extra=extra or {},
                )
                manifest.entries[product_id] = entry
                self._save_manifest_unlocked(manifest)
                transaction_succeeded = True
            except Exception as install_error:
                if not installed:
                    temporary.unlink(missing_ok=True)
                if installed and backup_created and backup is not None:
                    try:
                        os.replace(backup, destination)
                    except Exception as restore_error:
                        raise restore_error from install_error
                    rollback_restored = True
                    _fsync_directory(destination.parent)
                elif installed and not destination_existed:
                    destination.unlink(missing_ok=True)
                    _fsync_directory(destination.parent)
                raise
            finally:
                cleanup_backup = (
                    transaction_succeeded or not installed or rollback_restored
                )
                if backup is not None and cleanup_backup:
                    backup.unlink(missing_ok=True)
        return entry

    def store_text(
        self,
        product_id: str,
        destination: Path,
        text: str,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> CacheEntry:
        """Write and install UTF-8 text without exposing partial content."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        data = text.encode("utf-8")
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".part",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            return self.install_temp_file(
                product_id,
                temporary,
                destination,
                url,
                etag=etag,
                last_modified=last_modified,
                content_sha256=hashlib.sha256(data).hexdigest(),
                extra=extra,
            )
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def resolved_path(self, product_id: str) -> Path | None:
        entry = self.get_entry(product_id)
        if entry is None:
            return None
        p = Path(entry.path)
        return p if p.exists() else None
