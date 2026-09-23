"""Geospatial agent — real A* route computation over GEBCO bathymetry
with India–Sri Lanka IMBL geofencing.
"""

from __future__ import annotations

import logging

from shapely.geometry import LineString, Point, shape
import os
import json
import urllib.request

from app.agents.routing_engine import compute_route

logger = logging.getLogger("orca.agents.geospatial")

# ── India–Sri Lanka IMBL (1974 Agreement, Palk Strait / Adam's Bridge) ─────
#
# Coordinates from the 1974 Indo–Sri Lanka Maritime Boundary Agreement
# (UN Treaty Series Vol. 1488, No. 25399), Palk Strait / Adam's Bridge segment.
#
# Shapely convention: (longitude, latitude) — i.e. (x, y).
# Elsewhere in ORCA we use (lat, lon) for function args, but Shapely
# geometries use (lon, lat).  The constants below are already in (lon, lat).

IMBL_PALK_STRAIT_COORDS = [
    (80.0500, 10.0833),   # Position 1
    (79.5833,  9.9500),   # Position 2
    (79.3767,  9.6692),   # Position 3
    (79.5117,  9.3633),   # Position 4
    (79.5333,  9.2167),   # Position 5
    (79.5333,  9.1000),   # Position 6
]

IMBL_LINE = LineString(IMBL_PALK_STRAIT_COORDS)

# 3 nautical miles caution buffer
# 1 nm = 1.852 km.  At the equator 1° ≈ 111.32 km, so
# 3 nm = 3 × 1.852 = 5.556 km ≈ 5.556 / 111.32 ≈ 0.04992°
# We round to 0.05° which is conservative (slightly wider buffer).
IMBL_CAUTION_BUFFER_DEG = 0.05
IMBL_CAUTION_ZONE = IMBL_LINE.buffer(IMBL_CAUTION_BUFFER_DEG)

NM_PER_DEGREE = 60.0  # approximate, for distance reporting



_MPA_FEATURES = []
_MPA_LOADED = False

def load_mpa_data():
    global _MPA_FEATURES, _MPA_LOADED
    if _MPA_LOADED: return
    
    import os, json
    try:
        base_dir = os.path.dirname(__file__)
        mpa_path = os.path.join(base_dir, 'real_mpa_polygons.json')
        if os.path.exists(mpa_path):
            with open(mpa_path, 'r') as f:
                data = json.load(f)
                _MPA_FEATURES = data.get('features', [])
                logger.info(f"Loaded {len(_MPA_FEATURES)} real MPA polygons from WDPA/local source.")
    except Exception as e:
        logger.error(f"Failed to load real MPA polygons: {e}")
    _MPA_LOADED = True

def check_mpa_violations(waypoints: list[dict]) -> dict:
    load_mpa_data()
    if len(waypoints) < 2 or not _MPA_FEATURES:
        return {"mpa_caution": False, "mpa_name": None}
        
    route_coords = [(wp["lon"], wp["lat"]) for wp in waypoints]
    route_line = LineString(route_coords)
    
    for f in _MPA_FEATURES:
        try:
            poly = shape(f["geometry"])
            if route_line.intersects(poly):
                sector_name = f.get("properties", {}).get("SECTORNAME", "Unknown MPA")
                logger.info(f"MPA CAUTION: Route intersects MPA/Sector: {sector_name}")
                return {"mpa_caution": True, "mpa_name": sector_name}
        except Exception:
            continue
            
    return {"mpa_caution": False, "mpa_name": None}

def check_imbl_violations(waypoints: list[dict]) -> dict:
    """Deterministic IMBL geofencing check (pure Python/Shapely, no LLM).

    Args:
        waypoints: list of dicts with 'lat' and 'lon' keys.

    Returns:
        dict with keys:
        - imbl_hard_violation (bool): True if route crosses the IMBL line
        - imbl_caution_zone (bool): True if any waypoint is in the 3nm buffer
        - min_distance_to_imbl_nm (float | None): minimum distance in nm
    """
    if len(waypoints) < 2:
        return {
            "imbl_hard_violation": False,
            "imbl_caution_zone": False,
            "min_distance_to_imbl_nm": None,
        }

    # Build route LineString in (lon, lat) for Shapely
    route_coords = [(wp["lon"], wp["lat"]) for wp in waypoints]
    route_line = LineString(route_coords)

    # Hard violation: does the route line intersect the IMBL boundary?
    hard_violation = route_line.intersects(IMBL_LINE)

    # Caution zone: does any waypoint fall within the 3nm buffer?
    caution_zone = False
    min_dist_deg = float("inf")

    for wp in waypoints:
        pt = Point(wp["lon"], wp["lat"])
        dist = pt.distance(IMBL_LINE)  # in degrees
        if dist < min_dist_deg:
            min_dist_deg = dist

        if IMBL_CAUTION_ZONE.contains(pt) and not IMBL_LINE.intersects(
            Point(wp["lon"], wp["lat"])
        ):
            caution_zone = True

    # Convert minimum distance from degrees to nautical miles (approximate)
    min_dist_nm = round(min_dist_deg * NM_PER_DEGREE, 2)

    logger.info(
        "IMBL check: hard_violation=%s, caution_zone=%s, min_dist=%.2f nm",
        hard_violation, caution_zone, min_dist_nm,
    )

    return {
        "imbl_hard_violation": hard_violation,
        "imbl_caution_zone": caution_zone,
        "min_distance_to_imbl_nm": min_dist_nm,
    }


def get_route_between(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    vessel_draft_m: float,
    vessel_speed_knots: float | None = None,
    route_profile: str = "fishing",
) -> dict:
    """Compute an optimised maritime route between two coordinates.

    Uses A* pathfinding over real GEBCO 2020 bathymetric depth data,
    avoiding land and shallow water cells.  After computing the route,
    it also checks for IMBL boundary violations.
    """
    logger.info(f"Computing route: origin({origin_lat}, {origin_lon}) to dest({dest_lat}, {dest_lon}) [Profile: {route_profile}]")

    result = compute_route(
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        vessel_draft_m=vessel_draft_m,
        vessel_speed_knots=vessel_speed_knots,
        route_profile=route_profile,
    )

    # Run IMBL geofencing check on computed waypoints
    waypoints = result.get("waypoints", [])
    if waypoints:
        imbl_check = check_imbl_violations(waypoints)
        result.update(imbl_check)
        
        mpa_check = check_mpa_violations(waypoints)
        result.update(mpa_check)

        if imbl_check["imbl_hard_violation"]:
            logger.warning(
                "IMBL HARD VIOLATION: Route from (%.4f, %.4f) to (%.4f, %.4f) "
                "crosses the India–Sri Lanka maritime boundary!",
                origin_lat, origin_lon, dest_lat, dest_lon,
            )
            result["error"] = (
                "Route crosses the India–Sri Lanka International Maritime "
                "Boundary Line (IMBL). This route cannot be used. "
                "Request a different destination within Indian waters."
            )
        elif imbl_check["imbl_caution_zone"]:
            logger.warning(
                "IMBL CAUTION: Route passes within 3nm of the IMBL "
                "(min distance: %.2f nm)",
                imbl_check["min_distance_to_imbl_nm"],
            )

    return result
