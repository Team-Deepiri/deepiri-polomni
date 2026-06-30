"""Visualization data API for the React frontend."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from polomni.viz.multiverse import (
    branch_simplex,
    closed_loop_panel,
    district_graph_3d,
    falsification_panel,
    landscape_surface,
    scar_sphere,
    stream_flux_series,
)

router = APIRouter(tags=["viz"])


@router.get("/district-graph")
def get_district_graph(
    choices: int = Query(default=5, ge=2, le=20),
    districts: int = Query(default=1, ge=1, le=5),
    steps: int = Query(default=2, ge=1, le=10),
    policy: str = Query(default="uniform"),
) -> dict:
    return district_graph_3d(choices=choices, districts=districts, steps=steps, policy=policy)


@router.get("/closed-loop")
def get_closed_loop(
    steps: int = Query(default=3, ge=1, le=8),
    choices: int = Query(default=4, ge=2, le=12),
    nside: int = Query(default=32, ge=8, le=128),
    policy: str = Query(default="axis_biased"),
) -> dict:
    return closed_loop_panel(steps=steps, num_choices=choices, nside=nside, policy=policy)


@router.get("/landscape")
def get_landscape(grid_size: int = Query(default=24, ge=8, le=64)) -> dict:
    return landscape_surface(grid_size=grid_size)


@router.get("/scar-sphere")
def get_scar_sphere(
    synthetic: bool = Query(default=True),
    nside: int = Query(default=32, ge=8, le=256),
    map_product: str = Query(default="wmap_k_band"),
) -> dict:
    return scar_sphere(synthetic=synthetic, nside=nside, map_product_id=map_product)


@router.get("/stream-flux")
def get_stream_flux(packets: int = Query(default=5, ge=2, le=20)) -> dict:
    return stream_flux_series(packets=packets)


@router.get("/branch-simplex")
def get_branch_simplex(choices: int = Query(default=5, ge=2, le=12)) -> dict:
    return branch_simplex(choices=choices)


@router.get("/falsification")
def get_falsification() -> dict:
    return falsification_panel()
