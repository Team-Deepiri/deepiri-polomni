"""Lab dashboard static UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["dashboard"])

_DASHBOARD = Path(__file__).resolve().parent.parent / "static" / "dashboard.html"


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> HTMLResponse:
    """Serve the Polomni lab dashboard."""
    html = _DASHBOARD.read_text(encoding="utf-8")
    return HTMLResponse(content=html)
