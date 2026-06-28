"""FastAPI dependencies for the Polomni REST API."""

from __future__ import annotations

from polomni.observatory.pipeline.cache import DataCache


def get_cache() -> DataCache:
    """Return the shared filesystem data cache."""
    return DataCache()
