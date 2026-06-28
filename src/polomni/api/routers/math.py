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
def run_proofs(strict: bool = False, real_data: bool = False) -> dict:
    suite = prove_all(save=True, strict=strict, real_data=real_data)
    return suite.to_dict()


@router.post("/prove/strict")
def run_proofs_strict(real_data: bool = True) -> dict:
    suite = prove_all(save=True, strict=True, real_data=real_data)
    return suite.to_dict()
