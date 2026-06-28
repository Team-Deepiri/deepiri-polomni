"""FastAPI application factory for the Polomni lab API."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from polomni.api.routers import dashboard, data, health, math, metrics, observatory, stream, study, viz

_FRONTEND_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"


def create_app() -> FastAPI:
    """Build and configure the Polomni REST API."""
    app = FastAPI(title="Deepiri Polomni Lab", version="0.2.0")

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
    app.include_router(math.router, prefix="/math")
    app.include_router(viz.router, prefix="/viz")
    app.include_router(data.router, prefix="/data")
    app.include_router(observatory.router, prefix="/observatory")
    app.include_router(study.router, prefix="/study")
    app.include_router(stream.router, prefix="/stream")

    if _FRONTEND_DIST.is_dir() and (_FRONTEND_DIST / "index.html").is_file():
        assets = _FRONTEND_DIST / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

        @app.get("/app")
        @app.get("/app/{path:path}")
        def frontend_spa(path: str = "") -> FileResponse:
            return FileResponse(_FRONTEND_DIST / "index.html")

    return app
