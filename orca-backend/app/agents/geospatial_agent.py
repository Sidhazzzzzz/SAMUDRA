"""Geospatial agent — real A* route computation over GEBCO bathymetry."""

from __future__ import annotations

import logging

from app.agents.routing_engine import compute_route

logger = logging.getLogger("orca.agents.geospatial")


def get_route_between(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    vessel_draft_m: float,
) -> dict:
    """Compute an optimised maritime route between two coordinates.

    Uses A* pathfinding over real GEBCO 2020 bathymetric depth data,
    avoiding land and shallow water cells.
    """
    logger.info("Computing A* route: (%.4f, %.4f) -> (%.4f, %.4f), draft=%.1fm",
                origin_lat, origin_lon, dest_lat, dest_lon, vessel_draft_m)

    result = compute_route(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        vessel_draft_m=vessel_draft_m,
    )

    return result
