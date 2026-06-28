"""Study API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from polomni.observatory.studies.gates import load_latest_result, run_p1_gates
from polomni.observatory.studies.p1_runner import run_p1_study

router = APIRouter(tags=["study"])


@router.get("/p1/gates")
def p1_gates() -> dict:
    return run_p1_gates().to_dict()


@router.get("/p1/result")
def p1_result() -> dict:
    data = load_latest_result()
    if data is None:
        raise HTTPException(404, "No RESULT.json — run POST /study/p1/run first")
    return data


@router.post("/p1/run")
def p1_run(calibration: bool = True, blind: bool = False) -> dict:
    if blind and calibration:
        calibration = False
    try:
        return run_p1_study(blind=blind, calibration=calibration or not blind)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
