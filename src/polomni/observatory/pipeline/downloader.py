"""HTTP streaming downloader with cache integration."""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from polomni.observatory.pipeline.cache import DataCache
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


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
        existing = cache.resolved_path(product.id)
        if existing is not None:
            return FetchResult(
                product_id=product.id,
                path=existing,
                downloaded=False,
                bytes_written=existing.stat().st_size,
                from_cache=True,
                etag=cache.get_entry(product.id).etag if cache.get_entry(product.id) else None,
            )

    entry = cache.get_entry(product.id)
    req = urllib.request.Request(product.url, method="GET")
    if entry and entry.etag and not force:
        req.add_header("If-None-Match", entry.etag)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 304 and dest.exists():
                cache.record(product.id, dest, product.url, etag=entry.etag if entry else None)
                return FetchResult(
                    product_id=product.id,
                    path=dest,
                    downloaded=False,
                    bytes_written=dest.stat().st_size,
                    from_cache=True,
                    etag=entry.etag if entry else None,
                )

            etag = resp.headers.get("ETag")
            tmp = dest.with_suffix(dest.suffix + ".part")
            written = 0
            with tmp.open("wb") as out:
                while True:
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    written += len(chunk)
            tmp.replace(dest)
            digest = _sha256_file(dest)
            cache.record(product.id, dest, product.url, etag=etag, content_sha256=digest)
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
            return FetchResult(
                product_id=product.id,
                path=dest,
                downloaded=False,
                bytes_written=dest.stat().st_size,
                from_cache=True,
                etag=entry.etag if entry else None,
            )
        raise
