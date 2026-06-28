"""Pipeline settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PipelineSettings:
    """Observatory data-pipeline configuration."""

    data_cache: Path
    fetch_timeout: float
    gw_poll_interval: float


@lru_cache(maxsize=1)
def get_settings() -> PipelineSettings:
    """Return cached pipeline settings (override via env for tests)."""
    cache_root = os.environ.get("POLOMNI_DATA_CACHE")
    if cache_root:
        data_cache = Path(cache_root).expanduser().resolve()
    else:
        data_cache = (Path.cwd() / "data" / "cache").resolve()

    return PipelineSettings(
        data_cache=data_cache,
        fetch_timeout=float(os.environ.get("POLOMNI_FETCH_TIMEOUT", "120")),
        gw_poll_interval=float(os.environ.get("POLOMNI_GW_POLL_INTERVAL", "300")),
    )


def reset_settings_cache() -> None:
    """Clear cached settings (useful in tests after env changes)."""
    get_settings.cache_clear()
