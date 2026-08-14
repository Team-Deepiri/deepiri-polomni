"""Offline concurrency and interruption tests for the observatory cache."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import threading
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from polomni.observatory.pipeline import cache as cache_module
from polomni.observatory.pipeline import downloader
from polomni.observatory.pipeline import filesystem
from polomni.observatory.pipeline.cache import CacheManifest, DataCache
from polomni.observatory.pipeline.catalog import (
    GWOSC_CATALOG_URL,
    GWOSC_EVENTS_PRODUCT_ID,
    DataProduct,
)
from polomni.observatory.pipeline.downloader import fetch_product
from polomni.observatory.pipeline.sources import gwosc
from polomni.observatory.pipeline.sources.gwosc import (
    GWCatalogSnapshot,
    GWEvent,
    load_cached_gwtc,
)


def _record_worker(
    root: str,
    product_id: str,
    barrier: Any,
    attempted: Any,
    finished: Any,
) -> None:
    cache = DataCache(Path(root))
    path = cache.root / product_id / "payload.txt"
    path.parent.mkdir(parents=True)
    path.write_text(product_id)
    barrier.wait()
    attempted.set()
    cache.record(product_id, path, f"https://example.test/{product_id}")
    finished.set()


def _hold_manifest_lock(root: str, acquired: Any, release: Any) -> None:
    cache = DataCache(Path(root))
    with cache._manifest_lock():
        acquired.set()
        release.wait()


def _cleanup_processes(processes: list[Any]) -> None:
    for process in processes:
        if process.is_alive():
            process.terminate()
    for process in processes:
        process.join(timeout=5)
    for process in processes:
        if process.is_alive():
            process.kill()
    for process in processes:
        process.join()


class _Response:
    status = 200

    def __init__(
        self,
        payload: bytes,
        *,
        barrier: threading.Barrier | None = None,
        fail: bool = False,
        etag: str = '"etag"',
    ) -> None:
        self.payload = payload
        self.barrier = barrier
        self.fail = fail
        self.headers = {
            "ETag": etag,
            "Last-Modified": "Fri, 07 Aug 2026 12:00:00 GMT",
        }
        self.reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if self.reads == 0:
            self.reads += 1
            if self.barrier:
                self.barrier.wait(timeout=10)
            return self.payload
        if self.fail:
            raise OSError("interrupted transfer")
        return b""


class _JsonResponse:
    status = 200
    headers: dict[str, str] = {}

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        return json.dumps(self.payload).encode()


def _product() -> DataProduct:
    return DataProduct(
        id="test_product",
        name="Test",
        url="https://example.test/product",
        kind="txt",
        tier="lite",
        description="Test",
        mission="Test",
        refresh_hours=0,
        filename="product.bin",
    )


def _gw_payload(name: str) -> dict[str, Any]:
    return {
        "results": [
            {
                "name": name,
                "gps": 123.0,
                "catalog": "GWTC",
                "detectors": ["H1", "L1"],
                "version": 1,
            }
        ],
        "next": None,
    }


def _seed_gw(cache: DataCache, name: str) -> None:
    snapshot = GWCatalogSnapshot(
        fetched_at=datetime(2026, 8, 7, tzinfo=timezone.utc),
        results_count=1,
        events=[GWEvent(name=name, gps=123.0, catalog="GWTC", detectors=["H1"])],
    )
    cache.store_text(
        GWOSC_EVENTS_PRODUCT_ID,
        cache.root / GWOSC_EVENTS_PRODUCT_ID / "gwtc_events.json",
        snapshot.model_dump_json(indent=2),
        GWOSC_CATALOG_URL,
        extra={"results_count": 1},
    )


def test_concurrent_records_preserve_every_entry(tmp_path: Path) -> None:
    ctx = multiprocessing.get_context("spawn")
    ids = [f"product_{index}" for index in range(4)]
    barrier = ctx.Barrier(len(ids))
    acquired = ctx.Event()
    release = ctx.Event()
    attempted = [ctx.Event() for _ in ids]
    finished = [ctx.Event() for _ in ids]
    holder = ctx.Process(
        target=_hold_manifest_lock,
        args=(str(tmp_path), acquired, release),
    )
    workers = [
        ctx.Process(
            target=_record_worker,
            args=(str(tmp_path), product_id, barrier, attempted[index], finished[index]),
        )
        for index, product_id in enumerate(ids)
    ]
    started: list[Any] = []
    try:
        holder.start()
        started.append(holder)
        assert acquired.wait(timeout=15)

        for process in workers:
            process.start()
            started.append(process)
        assert all(event.wait(timeout=15) for event in attempted)
        assert not any(event.is_set() for event in finished)

        release.set()
        for process in started:
            process.join(timeout=20)
        assert all(process.exitcode == 0 for process in started)
    finally:
        release.set()
        _cleanup_processes(started)

    assert set(DataCache(tmp_path).load_manifest().entries) == set(ids)


def test_manifest_lock_path_remains_stable(tmp_path: Path) -> None:
    cache = DataCache(tmp_path)

    with cache._manifest_lock():
        assert cache._manifest_lock_path.exists()

    assert cache._manifest_lock_path.exists()


def test_manifest_replace_failure_keeps_previous_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = DataCache(tmp_path)
    payload = tmp_path / "old" / "payload"
    payload.parent.mkdir()
    payload.write_text("old")
    cache.record("old", payload, "https://example.test/old")
    manifest_path = tmp_path / "manifest.json"
    previous = manifest_path.read_text()

    monkeypatch.setattr(
        cache_module,
        "atomic_replace",
        lambda source, destination: (_ for _ in ()).throw(OSError("replace failed")),
    )
    with pytest.raises(OSError, match="replace failed"):
        cache.save_manifest(CacheManifest())

    assert manifest_path.read_text() == previous
    assert cache.load_manifest().entries["old"].product_id == "old"
    assert list(tmp_path.glob(".manifest.json.*.tmp")) == []


def test_backup_link_failure_uses_durable_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = DataCache(tmp_path)
    destination = cache.root / "product" / "payload.bin"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"original")
    cache.record("product", destination, "https://example.test/original")
    previous_manifest = cache.load_manifest()
    incoming = destination.parent / ".incoming.part"
    incoming.write_bytes(b"replacement")

    monkeypatch.setattr(
        filesystem.os,
        "link",
        lambda source, target: (_ for _ in ()).throw(OSError("link failed")),
    )

    cache.install_temp_file(
        "product", incoming, destination, "https://example.test/replacement"
    )

    assert destination.read_bytes() == b"replacement"
    assert not incoming.exists()
    assert cache.load_manifest() != previous_manifest
    entry = cache.get_entry("product")
    assert entry is not None
    assert entry.url == "https://example.test/replacement"
    assert list(destination.parent.glob(".*.part")) == []
    assert list(destination.parent.glob(".*.bak")) == []
    assert list(destination.parent.glob(".*.tmp")) == []


def test_backup_copy_failure_leaves_original_untouched(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = DataCache(tmp_path)
    destination = cache.root / "product" / "payload.bin"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"original")
    cache.record("product", destination, "https://example.test/original")
    previous_manifest = cache.load_manifest()
    incoming = destination.parent / ".incoming.part"
    incoming.write_bytes(b"replacement")

    monkeypatch.setattr(
        filesystem.os,
        "link",
        lambda source, target: (_ for _ in ()).throw(OSError("link failed")),
    )
    monkeypatch.setattr(
        filesystem.shutil,
        "copyfileobj",
        lambda source, target: (_ for _ in ()).throw(OSError("copy failed")),
    )

    with pytest.raises(OSError, match="copy failed"):
        cache.install_temp_file(
            "product", incoming, destination, "https://example.test/replacement"
        )

    assert destination.read_bytes() == b"original"
    assert not incoming.exists()
    assert cache.load_manifest() == previous_manifest
    assert list(destination.parent.glob(".*.part")) == []
    assert list(destination.parent.glob(".*.bak")) == []
    assert list(destination.parent.glob(".*.tmp")) == []


def test_restore_failure_preserves_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = DataCache(tmp_path)
    destination = cache.root / "product" / "payload.bin"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"original")
    cache.record("product", destination, "https://example.test/original")
    previous_manifest = cache.load_manifest()
    monkeypatch.setattr(
        cache_module,
        "restore_rollback_backup",
        lambda source, target: (_ for _ in ()).throw(OSError("restore failed")),
    )
    monkeypatch.setattr(
        cache,
        "_save_manifest_unlocked",
        lambda manifest: (_ for _ in ()).throw(OSError("manifest failed")),
    )

    with pytest.raises(OSError, match="restore failed") as raised:
        cache.store_text(
            "product",
            destination,
            "replacement",
            "https://example.test/replacement",
        )

    assert isinstance(raised.value.__cause__, OSError)
    assert str(raised.value.__cause__) == "manifest failed"
    backups = list(destination.parent.glob(".*.bak"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"original"
    assert destination.read_bytes() == b"replacement"
    assert cache.load_manifest() == previous_manifest
    assert list(destination.parent.glob(".*.part")) == []


def test_filesystem_restore_failure_preserves_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "payload.bin"
    destination.write_bytes(b"replacement")
    backup = tmp_path / ".payload.bin.recovery.bak"
    backup.write_bytes(b"original")
    real_replace = filesystem.atomic_replace

    def fail_destination_replace(source: Path, target: Path) -> None:
        if Path(target) == destination:
            raise OSError("restore failed")
        real_replace(source, target)

    monkeypatch.setattr(filesystem, "atomic_replace", fail_destination_replace)

    with pytest.raises(OSError, match="restore failed"):
        filesystem.restore_rollback_backup(backup, destination)

    assert destination.read_bytes() == b"replacement"
    assert backup.read_bytes() == b"original"
    assert list(tmp_path.glob(".*.restore")) == []
    assert list(tmp_path.glob(".*.tmp")) == []


def test_malformed_manifest_is_not_destroyed(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text('{"entries":')
    cache = DataCache(tmp_path)
    payload = tmp_path / "new"
    payload.write_text("new")

    with pytest.raises(ValidationError):
        cache.record("new", payload, "https://example.test/new")
    assert path.read_text() == '{"entries":'


def test_concurrent_downloads_use_unique_temps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = DataCache(tmp_path)
    product = _product()
    barrier = threading.Barrier(2)
    payloads = iter([b"first", b"second"])
    response_lock = threading.Lock()

    def urlopen(request: Any, timeout: float) -> _Response:
        with response_lock:
            payload = next(payloads)
        return _Response(payload, barrier=barrier, etag=payload.decode())

    temps: list[Path] = []
    install = cache.install_temp_file

    def tracked(product_id: str, temporary: Path, destination: Path, url: str, **kw: Any):
        temps.append(temporary)
        return install(product_id, temporary, destination, url, **kw)

    monkeypatch.setattr(downloader.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(cache, "install_temp_file", tracked)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: fetch_product(product, cache, force=True), range(2)))

    destination = cache.root / product.id / product.cache_filename()
    data = destination.read_bytes()
    entry = cache.get_entry(product.id)
    assert all(result.downloaded for result in results)
    assert len(set(temps)) == 2
    assert data in {b"first", b"second"}
    assert entry is not None
    assert entry.content_sha256 == hashlib.sha256(data).hexdigest()
    assert list(destination.parent.glob(".*.part")) == []
    assert list(destination.parent.glob(".*.bak")) == []
    assert list(destination.parent.glob(".*.tmp")) == []
    assert list(destination.parent.glob(".*.restore")) == []


def test_interrupted_download_keeps_existing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = DataCache(tmp_path)
    product = _product()
    destination = cache.root / product.id / product.cache_filename()
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"existing")
    digest = hashlib.sha256(b"existing").hexdigest()
    cache.record(product.id, destination, product.url, content_sha256=digest)
    monkeypatch.setattr(
        downloader.urllib.request,
        "urlopen",
        lambda request, timeout: _Response(b"partial", fail=True),
    )

    with pytest.raises(OSError, match="interrupted"):
        fetch_product(product, cache, force=True)
    assert destination.read_bytes() == b"existing"
    assert cache.get_entry(product.id).content_sha256 == digest
    assert list(destination.parent.glob(".*.part")) == []


def test_304_refreshes_only_freshness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = DataCache(tmp_path)
    product = _product()
    destination = cache.root / product.id / product.cache_filename()
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"unchanged")
    checksum = hashlib.sha256(b"unchanged").hexdigest()
    cache.record(
        product.id,
        destination,
        product.url,
        etag='"etag"',
        last_modified="Thu, 06 Aug 2026 12:00:00 GMT",
        content_sha256=checksum,
        extra={"custom": 7},
    )
    manifest = cache.load_manifest()
    old = datetime(2020, 1, 1, tzinfo=timezone.utc)
    manifest.entries[product.id] = manifest.entries[product.id].model_copy(
        update={"fetched_at": old}
    )
    cache.save_manifest(manifest)
    previous_stat = destination.stat()
    headers: dict[str, str] = {}

    def not_modified(request: Any, timeout: float) -> None:
        headers.update({key.lower(): value for key, value in request.header_items()})
        raise urllib.error.HTTPError(request.full_url, 304, "Not Modified", {}, None)

    monkeypatch.setattr(downloader.urllib.request, "urlopen", not_modified)
    result = fetch_product(product, cache)
    entry = cache.get_entry(product.id)

    assert result.from_cache and not result.downloaded
    assert entry is not None and entry.fetched_at > old
    assert entry.etag == '"etag"'
    assert entry.last_modified == "Thu, 06 Aug 2026 12:00:00 GMT"
    assert entry.content_sha256 == checksum
    assert entry.extra == {"custom": 7}
    assert cache.is_fresh(product.id, 1)
    assert destination.stat().st_mtime_ns == previous_stat.st_mtime_ns
    assert headers["if-none-match"] == '"etag"'
    assert headers["if-modified-since"] == entry.last_modified


def test_gw_snapshot_replace_and_failure_rollback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = DataCache(tmp_path)
    _seed_gw(cache, "GWOLD")
    monkeypatch.setattr(
        gwosc.urllib.request,
        "urlopen",
        lambda request, timeout: _JsonResponse(_gw_payload("GWNEW")),
    )
    gwosc.fetch_gwtc_events(cache, max_pages=1)
    assert load_cached_gwtc(cache).events[0].name == "GWNEW"

    previous_manifest = (cache.root / "manifest.json").read_text()
    monkeypatch.setattr(
        cache,
        "_save_manifest_unlocked",
        lambda manifest: (_ for _ in ()).throw(OSError("manifest failed")),
    )
    with pytest.raises(OSError, match="manifest failed"):
        gwosc.fetch_gwtc_events(cache, max_pages=1)

    assert load_cached_gwtc(cache).events[0].name == "GWNEW"
    assert (cache.root / "manifest.json").read_text() == previous_manifest
    directory = cache.root / GWOSC_EVENTS_PRODUCT_ID
    assert list(directory.glob(".*.part")) == []
    assert list(directory.glob(".*.bak")) == []
    assert list(directory.glob(".*.tmp")) == []
    assert list(directory.glob(".*.restore")) == []
