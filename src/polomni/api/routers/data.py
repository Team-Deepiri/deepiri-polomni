"""Data catalog, cache status, and fetch routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from polomni.api.deps import get_cache
from polomni.api.schemas import (
    CacheStatus,
    CatalogProduct,
    FetchRequest,
    FetchResponse,
    FetchResultItem,
    GWEventSummary,
    GWEventsResponse,
)
from polomni.observatory.pipeline.cache import DataCache
from polomni.observatory.pipeline.catalog import CATALOG, get_product
from polomni.observatory.pipeline.downloader import fetch_product
from polomni.observatory.pipeline.processor import list_cached_products
from polomni.observatory.pipeline.sources.gwosc import fetch_gwtc_events, load_cached_gwtc

router = APIRouter(tags=["data"])


@router.get("/catalog", response_model=list[CatalogProduct])
def catalog() -> list[CatalogProduct]:
    """List available CATALOG data products."""
    return [
        CatalogProduct(
            id=p.id,
            name=p.name,
            tier=p.tier,
            mission=p.mission,
            description=p.description,
            kind=p.kind,
        )
        for p in CATALOG.values()
    ]


@router.get("/status", response_model=list[CacheStatus])
def status(cache: Annotated[DataCache, Depends(get_cache)]) -> list[CacheStatus]:
    """Return cached files with sizes."""
    paths = list_cached_products(cache)
    out: list[CacheStatus] = []
    for product_id, path in paths.items():
        if path is not None:
            out.append(
                CacheStatus(
                    product_id=product_id,
                    cached=True,
                    path=str(path),
                    size_bytes=path.stat().st_size,
                )
            )
        else:
            out.append(CacheStatus(product_id=product_id, cached=False))
    return out


@router.post("/fetch", response_model=FetchResponse)
def fetch_data(
    body: FetchRequest,
    cache: Annotated[DataCache, Depends(get_cache)],
) -> FetchResponse:
    """Download product IDs into the local cache."""
    results: list[FetchResultItem] = []
    for pid in body.product_ids:
        try:
            product = get_product(pid)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        fetched = fetch_product(product, cache, force=body.force)
        results.append(
            FetchResultItem(
                product_id=pid,
                path=str(fetched.path),
                bytes_written=fetched.bytes_written,
                from_cache=fetched.from_cache and not fetched.downloaded,
            )
        )

    gw_count: int | None = None
    if body.fetch_gw:
        snap = fetch_gwtc_events(cache)
        gw_count = snap.results_count

    return FetchResponse(results=results, gw_events_count=gw_count)


@router.get("/gw/events", response_model=GWEventsResponse)
def gw_events(cache: Annotated[DataCache, Depends(get_cache)]) -> GWEventsResponse:
    """Load cached GWTC JSON and return count plus recent events."""
    snap = load_cached_gwtc(cache)
    if snap is None:
        raise HTTPException(status_code=404, detail="GWTC catalog not cached; POST /data/fetch first")
    recent = [
        GWEventSummary(
            name=e.name,
            gps=e.gps,
            catalog=e.catalog,
            detectors=e.detectors,
        )
        for e in snap.events[:10]
    ]
    return GWEventsResponse(count=snap.results_count, recent=recent)
