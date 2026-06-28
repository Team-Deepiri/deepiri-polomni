"""Real-time online data ingestion for RBLE observatory."""

from polomni.observatory.pipeline.cache import DataCache, default_cache_dir
from polomni.observatory.pipeline.catalog import CATALOG, DataProduct, get_product, list_products
from polomni.observatory.pipeline.downloader import FetchResult, fetch_product
from polomni.observatory.pipeline.config import get_settings, reset_settings_cache
from polomni.observatory.pipeline.events import EventLog, PipelineEvent
from polomni.observatory.pipeline.processor import (
    PipelineResult,
    calibrate_from_power_spectrum,
    correlate_gw_rble,
    ingest_standard_data,
    run_rble_pipeline,
)
from polomni.observatory.pipeline.scheduler import WatchEvent, poll_once, watch_realtime

__all__ = [
    "CATALOG",
    "DataCache",
    "DataProduct",
    "EventLog",
    "FetchResult",
    "PipelineEvent",
    "PipelineResult",
    "WatchEvent",
    "calibrate_from_power_spectrum",
    "correlate_gw_rble",
    "default_cache_dir",
    "fetch_product",
    "get_product",
    "get_settings",
    "ingest_standard_data",
    "list_products",
    "poll_once",
    "reset_settings_cache",
    "run_rble_pipeline",
    "watch_realtime",
]
