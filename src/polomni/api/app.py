"""FastAPI application factory for the Polomni lab API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from polomni.api.routers import dashboard, data, health, metrics, observatory, stream


def create_app() -> FastAPI:
    """Build and configure the Polomni REST API."""
    app = FastAPI(title="Deepiri Polomni Lab", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(dashboard.router)
    app.include_router(data.router, prefix="/data")
    app.include_router(observatory.router, prefix="/observatory")
    app.include_router(stream.router, prefix="/stream")

    return app
