"""Math proof API routes."""

from __future__ import annotations

from fastapi import APIRouter

from polomni.math.catalog import EQUATION_CATALOG
from polomni.math.proofs.base import load_cached_suite, prove_all

router = APIRouter(tags=["math"])


@router.get("/equations")
def list_equations() -> dict:
    return {"equations": EQUATION_CATALOG}


@router.get("/proofs")
def get_proofs() -> dict:
    suite = load_cached_suite()
    if suite is None:
        return {"cached": False, "message": "No proof run yet. POST /math/prove first."}
    return {"cached": True, **suite.to_dict()}


@router.post("/prove")
def run_proofs() -> dict:
    suite = prove_all(save=True)
    return suite.to_dict()
