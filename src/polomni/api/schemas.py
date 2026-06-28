"""Pydantic request/response models for the Polomni REST API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class RootResponse(BaseModel):
    name: str
    framework: str


class CatalogProduct(BaseModel):
    id: str
    name: str
    tier: str
    mission: str
    description: str
    kind: str


class CacheStatus(BaseModel):
    product_id: str
    cached: bool
    path: str | None = None
    size_bytes: int | None = None


class FetchRequest(BaseModel):
    product_ids: list[str] = Field(default_factory=list)
    force: bool = False
    fetch_gw: bool = True


class FetchResultItem(BaseModel):
    product_id: str
    path: str
    bytes_written: int
    from_cache: bool


class FetchResponse(BaseModel):
    results: list[FetchResultItem]
    gw_events_count: int | None = None


class PipelineRequest(BaseModel):
    map_product: str | None = None
    nside: int = 128
    nulls: int = 30
    force: bool = False


class PipelineResponse(BaseModel):
    ran_at: datetime
    map_product_id: str
    nside_used: int
    rble_score: float
    preferred_axis: list[float]
    n_hat: list[float]
    null_sigma: float
    falsification_flags: dict[str, bool]
    metadata: dict[str, Any]
    timestamp: datetime
    planck_lambda: float | None = None
    report_path: str | None = None
    gw_new_events: int = 0


class GWEventSummary(BaseModel):
    name: str
    gps: float
    catalog: str
    detectors: list[str] = Field(default_factory=list)


class GWEventsResponse(BaseModel):
    count: int
    recent: list[GWEventSummary]


class ScanRequest(BaseModel):
    nside: int = 64
    synthetic: bool = True
    map_product_id: str | None = None
    nulls: int = 20
    seed: int = 42
    map_path: str | None = None


class ScanResponse(BaseModel):
    rble_score: float
    preferred_axis: list[float]
    n_hat: list[float]
    null_sigma: float
    falsification_flags: dict[str, bool]
    metadata: dict[str, Any]
    timestamp: datetime


class ReportSummary(BaseModel):
    filename: str
    path: str
    size_bytes: int


class ReportsListResponse(BaseModel):
    reports: list[ReportSummary]
