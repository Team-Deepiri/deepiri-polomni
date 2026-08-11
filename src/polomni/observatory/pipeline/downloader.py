"""HTTP streaming downloader with cache integration."""

from __future__ import annotations

import hashlib
import os
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from polomni.observatory.pipeline.cache import CacheEntry, DataCache
from polomni.observatory.pipeline.catalog import DataProduct
from polomni.observatory.pipeline.config import get_settings


@dataclass
class FetchResult:
    product_id: str
    path: Path
    downloaded: bool
    bytes_written: int
    from_cache: bool
    etag: str | None = None


def _not_modified_result(
    product: DataProduct,
    cache: DataCache,
    entry: CacheEntry | None,
) -> FetchResult:
    if entry is None:
        raise RuntimeError(f"Received HTTP 304 without a cache entry for {product.id!r}")
    path = Path(entry.path)
    if not path.exists():
        raise FileNotFoundError(f"Received HTTP 304 but cached file is missing: {path}")
    refreshed = cache.refresh_entry(product.id)
    return FetchResult(
        product_id=product.id,
        path=path,
        downloaded=False,
        bytes_written=path.stat().st_size,
        from_cache=True,
        etag=refreshed.etag,
    )


def fetch_product(
    product: DataProduct,
    cache: DataCache | None = None,
    *,
    force: bool = False,
    timeout: float | None = None,
) -> FetchResult:
    """Download *product* into cache if missing or stale.

    Uses conditional GET when an ETag is stored. Streams large FITS files.
    """
    cache = cache or DataCache()
    timeout = timeout if timeout is not None else get_settings().fetch_timeout
    dest_dir = cache.root / product.id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / product.cache_filename()

    if not force and cache.is_fresh(product.id, product.refresh_hours):
        entry = cache.get_entry(product.id)
        existing = cache.resolved_path(product.id)
        if existing is not None:
            return FetchResult(
                product_id=product.id,
                path=existing,
                downloaded=False,
                bytes_written=existing.stat().st_size,
                from_cache=True,
                etag=entry.etag if entry else None,
            )

    entry = cache.get_entry(product.id)
    req = urllib.request.Request(product.url, method="GET")
    if entry and entry.etag and not force:
        req.add_header("If-None-Match", entry.etag)
    if entry and entry.last_modified and not force:
        req.add_header("If-Modified-Since", entry.last_modified)

    temporary: Path | None = None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 304 and dest.exists():
                return _not_modified_result(product, cache, entry)

            etag = resp.headers.get("ETag")
            last_modified = resp.headers.get("Last-Modified")
            digest = hashlib.sha256()
            written = 0
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=dest_dir,
                prefix=f".{dest.name}.",
                suffix=".part",
                delete=False,
            ) as out:
                temporary = Path(out.name)
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    digest.update(chunk)
                    written += len(chunk)
                out.flush()
                os.fsync(out.fileno())
            cache.install_temp_file(
                product.id,
                temporary,
                dest,
                product.url,
                etag=etag,
                last_modified=last_modified,
                content_sha256=digest.hexdigest(),
            )
            return FetchResult(
                product_id=product.id,
                path=dest,
                downloaded=True,
                bytes_written=written,
                from_cache=False,
                etag=etag,
            )
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and dest.exists():
            return _not_modified_result(product, cache, entry)
        raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
