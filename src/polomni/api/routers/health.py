"""Health and root metadata routes."""

from __future__ import annotations

from fastapi import APIRouter

from polomni.api.schemas import HealthResponse, RootResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe."""
    return HealthResponse(status="ok", service="polomni-lab")


@router.get("/", response_model=RootResponse)
def root() -> RootResponse:
    """Service metadata."""
    return RootResponse(name="deepiri-polomni", framework="RBLE")
