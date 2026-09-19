"""A* maritime routing engine over GEBCO 2020 bathymetric data.

Fetches real ocean-depth data from the Open Topo Data API (GEBCO 2020),
builds a navigability grid for the Gulf of Mannar / Palk Bay region,
and runs A* search to find the shortest safe maritime route between
two points, avoiding land and shallow water.

Grid specification:
  - Bounding box: lat 9.0–9.5, lon 79.0–79.8
  - Step: 0.025°
  - Grid: 21 rows × 33 cols = 693 points
  - Batched API calls: 7 × 100 locations (with 1s sleep between)
"""

from __future__ import annotations

import heapq
import json
import logging
import math
import os
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("orca.agents.routing_engine")

# ── Grid configuration ──────────────────────────────────────────────────────

LAT_MIN, LAT_MAX = 9.0, 9.5
LON_MIN, LON_MAX = 79.0, 79.8
GRID_STEP = 0.025  # degrees

# Safety thresholds
MIN_SAFE_DEPTH_M = -3.0  # elevation must be <= this (i.e. depth >= 3m)
DEFAULT_VESSEL_SPEED_KNOTS = 8.0
KM_PER_NAUTICAL_MILE = 1.852

# API configuration
OPENTOPODATA_URL = "https://api.opentopodata.org/v1/gebco2020"
BATCH_SIZE = 100
RATE_LIMIT_SLEEP_S = 1.1  # slightly over 1s to be safe

# Cache file path
CACHE_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = CACHE_DIR / "bathymetry_cache_mannar.json"


# ── IMBL extension point ────────────────────────────────────────────────────


def imbl_barrier_cost(lat: float, lon: float) -> float:
    """Additional traversal cost for cells near the India–Sri Lanka IMBL.

    Uses the verified 1974 Agreement boundary coordinates from
    geospatial_agent.  Returns float('inf') for cells on the IMBL line
    itself (hard exclusion) or a large finite penalty for cells within
    the 3nm caution buffer (soft avoidance to discourage routing near
    the boundary).
    """
    from shapely.geometry import Point

    # Lazy import to avoid circular dependency at module load time
    from app.agents.geospatial_agent import IMBL_LINE, IMBL_CAUTION_ZONE

    pt = Point(lon, lat)  # Shapely uses (x=lon, y=lat)

    # Hard exclusion: on or past the IMBL line
    if IMBL_LINE.distance(pt) < 1e-6:
        return float("inf")

    # Soft penalty: within 3nm caution buffer
    if IMBL_CAUTION_ZONE.contains(pt):
        return 50.0  # Large penalty in km-equivalent units

    return 0.0


# ── Haversine distance ──────────────────────────────────────────────────────


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── Grid construction ───────────────────────────────────────────────────────


def _build_grid_coords() -> list[tuple[float, float]]:
    """Generate all (lat, lon) grid points."""
    coords = []
    lat = LAT_MIN
    while lat <= LAT_MAX + 1e-9:
        lon = LON_MIN
        while lon <= LON_MAX + 1e-9:
            coords.append((round(lat, 4), round(lon, 4)))
            lon += GRID_STEP
        lat += GRID_STEP
    return coords


def _fetch_bathymetry(coords: list[tuple[float, float]]) -> dict[str, float]:
    """Fetch elevation for all grid coords from Open Topo Data API.

    Returns a dict mapping "lat,lon" string keys to elevation in metres.
    """
    total = len(coords)
    num_batches = math.ceil(total / BATCH_SIZE)
    logger.info("Fetching bathymetry: %d points in %d batches", total, num_batches)

    elevations: dict[str, float] = {}

    with httpx.Client(timeout=30.0) as client:
        for batch_idx in range(num_batches):
            start = batch_idx * BATCH_SIZE
            end = min(start + BATCH_SIZE, total)
            batch = coords[start:end]

            locations_str = "|".join(f"{lat},{lon}" for lat, lon in batch)

            logger.info("  Batch %d/%d: points %d–%d (%d locations)",
                        batch_idx + 1, num_batches, start, end - 1, len(batch))

            resp = client.get(OPENTOPODATA_URL, params={"locations": locations_str})
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") != "OK":
                raise RuntimeError(
                    f"OpenTopoData API returned non-OK status: {data}"
                )

            for result in data["results"]:
                rlat = result["location"]["lat"]
                rlng = result["location"]["lng"]
                elev = result["elevation"]
                key = f"{round(rlat, 4)},{round(rlng, 4)}"
                elevations[key] = elev

            # Rate-limit: sleep between batches (not after last one)
            if batch_idx < num_batches - 1:
                time.sleep(RATE_LIMIT_SLEEP_S)

    logger.info("Fetched %d elevation values", len(elevations))
    return elevations


def _load_or_fetch_bathymetry() -> dict[str, float]:
    """Load bathymetry from cache, or fetch from API and cache it."""
    if CACHE_FILE.exists():
        logger.info("Loading bathymetry from cache: %s", CACHE_FILE)
        with open(CACHE_FILE, "r") as f:
            return json.load(f)

    logger.info("No bathymetry cache found, fetching from OpenTopoData API...")
    coords = _build_grid_coords()
    elevations = _fetch_bathymetry(coords)

    # Save to cache
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(elevations, f, indent=2)
    logger.info("Bathymetry cached to %s (%d entries)", CACHE_FILE, len(elevations))

    return elevations


# ── Navigability grid ───────────────────────────────────────────────────────


class NavGrid:
    """Navigation grid with elevation data and traversability information."""

    def __init__(self, elevations: dict[str, float], min_safe_depth: float = MIN_SAFE_DEPTH_M):
        self.elevations = elevations
        self.min_safe_depth = min_safe_depth

        # Build ordered lat/lon axes
        lats = set()
        lons = set()
        for key in elevations:
            lat_s, lon_s = key.split(",")
            lats.add(float(lat_s))
            lons.add(float(lon_s))

        self.lats = sorted(lats)
        self.lons = sorted(lons)
        self.nrows = len(self.lats)
        self.ncols = len(self.lons)

        # Build index lookups for fast row/col resolution
        self._lat_to_row = {lat: i for i, lat in enumerate(self.lats)}
        self._lon_to_col = {lon: j for j, lon in enumerate(self.lons)}

        # Build traversability mask
        self._traversable: set[tuple[int, int]] = set()
        self._excluded_count = 0
        for i, lat in enumerate(self.lats):
            for j, lon in enumerate(self.lons):
                key = f"{lat},{lon}"
                elev = self.elevations.get(key)
                if elev is None:
                    self._excluded_count += 1
                    continue
                if elev >= 0:
                    # Land or exposed
                    self._excluded_count += 1
                    continue
                if elev > self.min_safe_depth:
                    # Too shallow (depth < 3m)
                    self._excluded_count += 1
                    continue
                self._traversable.add((i, j))

        total = self.nrows * self.ncols
        logger.info("NavGrid: %d×%d = %d cells, %d traversable, %d excluded (land/shallow)",
                     self.nrows, self.ncols, total,
                     len(self._traversable), self._excluded_count)

    def is_traversable(self, row: int, col: int) -> bool:
        return (row, col) in self._traversable

    def get_coords(self, row: int, col: int) -> tuple[float, float]:
        return self.lats[row], self.lons[col]

    def snap_to_nearest_valid(self, lat: float, lon: float) -> tuple[int, int] | None:
        """Find the nearest traversable grid cell to the given coordinates."""
        best = None
        best_dist = float("inf")
        for (r, c) in self._traversable:
            glat, glon = self.lats[r], self.lons[c]
            d = haversine_km(lat, lon, glat, glon)
            if d < best_dist:
                best_dist = d
                best = (r, c)
        return best

    def get_neighbors(self, row: int, col: int) -> list[tuple[int, int]]:
        """Return 8-connected neighbors that are traversable."""
        neighbors = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < self.nrows and 0 <= nc < self.ncols:
                    if self.is_traversable(nr, nc):
                        neighbors.append((nr, nc))
        return neighbors

    def edge_cost(self, r1: int, c1: int, r2: int, c2: int) -> float:
        """Cost of moving from cell (r1,c1) to (r2,c2).

        Base cost = haversine distance in km, plus any IMBL barrier cost.
        """
        lat1, lon1 = self.get_coords(r1, c1)
        lat2, lon2 = self.get_coords(r2, c2)
        base = haversine_km(lat1, lon1, lat2, lon2)

        # Extension point: add IMBL barrier cost if applicable
        barrier = imbl_barrier_cost(lat2, lon2)
        if barrier == float("inf"):
            return float("inf")

        return base + barrier

    @property
    def grid_stats(self) -> dict[str, int]:
        total = self.nrows * self.ncols
        return {
            "rows": self.nrows,
            "cols": self.ncols,
            "total_cells": total,
            "traversable_cells": len(self._traversable),
            "excluded_cells": self._excluded_count,
        }


# ── A* search ───────────────────────────────────────────────────────────────


def astar_search(
    grid: NavGrid,
    start: tuple[int, int],
    goal: tuple[int, int],
    extra_cost_func=None
) -> tuple[list[tuple[int, int]], float, int] | None:
    """Run A* search over the navigation grid.

    Args:
        grid:  The NavGrid to search over.
        start: (row, col) of the start cell.
        goal:  (row, col) of the goal cell.
        extra_cost_func: Optional callable (row, col) -> float

    Returns:
        (path, total_cost_km, nodes_explored) or None if no path exists.
        path is a list of (row, col) tuples from start to goal (inclusive).
    """
    goal_lat, goal_lon = grid.get_coords(*goal)

    # Priority queue: (f_score, counter, (row, col))
    counter = 0
    open_set: list[tuple[float, int, tuple[int, int]]] = []

    def h(r: int, c: int) -> float:
        """Admissible heuristic: straight-line haversine distance to goal."""
        lat, lon = grid.get_coords(r, c)
        return haversine_km(lat, lon, goal_lat, goal_lon)

    g_score: dict[tuple[int, int], float] = {start: 0.0}
    came_from: dict[tuple[int, int], tuple[int, int]] = {}

    heapq.heappush(open_set, (h(*start), counter, start))
    counter += 1
    nodes_explored = 0

    while open_set:
        f, _, current = heapq.heappop(open_set)

        if current == goal:
            # Reconstruct path
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path, g_score[goal], nodes_explored

        nodes_explored += 1

        for neighbor in grid.get_neighbors(*current):
            cost = grid.edge_cost(*current, *neighbor)
            if cost == float("inf"):
                continue
                
            if extra_cost_func:
                cost += extra_cost_func(*neighbor)

            tentative_g = g_score[current] + cost

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score = tentative_g + h(*neighbor)
                heapq.heappush(open_set, (f_score, counter, neighbor))
                counter += 1

    logger.warning("A* search found no path from %s to %s", start, goal)
    return None


# ── Public routing function ─────────────────────────────────────────────────

# Module-level singleton for the navigation grid (loaded once)
_nav_grid: NavGrid | None = None


def _get_nav_grid() -> NavGrid:
    """Get or initialize the navigation grid (singleton)."""
    global _nav_grid
    if _nav_grid is None:
        elevations = _load_or_fetch_bathymetry()
        _nav_grid = NavGrid(elevations)
    return _nav_grid


def compute_route(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    vessel_draft_m: float = 2.0,
    vessel_speed_knots: float | None = None,
    route_profile: str = "fishing"
) -> dict[str, Any]:
    """Compute a real A* maritime route between two coordinates.

    Snaps origin/destination to nearest valid grid cells, runs A*,
    and returns a full route result with waypoints, distance, and time.
    """
    grid = _get_nav_grid()

    if vessel_speed_knots is None:
        vessel_speed_knots = 12.0 if route_profile == "commercial" else DEFAULT_VESSEL_SPEED_KNOTS

    # Snap to nearest valid grid cells
    start_cell = grid.snap_to_nearest_valid(origin_lat, origin_lon)
    goal_cell = grid.snap_to_nearest_valid(dest_lat, dest_lon)

    if start_cell is None or goal_cell is None:
        return {
            "source": "A* over GEBCO 2020 bathymetry (OpenTopoData)",
            "error": "Could not snap origin or destination to a valid ocean cell",
            "origin": {"lat": origin_lat, "lon": origin_lon},
            "destination": {"lat": dest_lat, "lon": dest_lon},
            "waypoints": [],
            "distance_km": 0.0,
            "distance_nm": 0.0,
            "estimated_time_hrs": 0.0,
            "grid_stats": grid.grid_stats,
        }

    logger.info("A* routing: origin (%.4f, %.4f) snapped to cell %s, "
                "dest (%.4f, %.4f) snapped to cell %s",
                origin_lat, origin_lon, start_cell,
                dest_lat, dest_lon, goal_cell)

    extra_cost_func = None
    if route_profile == "commercial":
        try:
            from app.agents.pfz_agent import get_active_pfz
            bbox = [min(origin_lat, dest_lat)-1, min(origin_lon, dest_lon)-1,
                    max(origin_lat, dest_lat)+1, max(origin_lon, dest_lon)+1]
            pfz_data = get_active_pfz(bbox, origin_lat, origin_lon)
            
            from shapely.geometry import MultiLineString, LineString, Point
            lines = []
            for f in pfz_data.get("pfz_lines", []):
                geom = f.get("geometry", {})
                coords = geom.get("coordinates", [])
                if geom.get("type") == "MultiLineString":
                    for line in coords:
                        lines.append(LineString(line))
                elif geom.get("type") == "LineString":
                    lines.append(LineString(coords))
            
            pfz_geom = None
            if lines:
                pfz_geom = MultiLineString(lines)
            
            if pfz_geom:
                logger.info("Applying commercial PFZ avoidance penalty.")
                def pfz_penalty(r, c):
                    lat, lon = grid.get_coords(r, c)
                    # ~2km buffer is ~0.018 degrees
                    dist_deg = pfz_geom.distance(Point(lon, lat))
                    if dist_deg < 0.018:
                        return 10.0 # Heavy 10km additive penalty per step near PFZ
                    return 0.0
                extra_cost_func = pfz_penalty
        except Exception as e:
            logger.error(f"Error setting up commercial PFZ penalty: {e}")

    result = astar_search(grid, start_cell, goal_cell, extra_cost_func=extra_cost_func)

    if result is None:
        return {
            "source": "A* over GEBCO 2020 bathymetry (OpenTopoData)",
            "error": "No navigable path found between origin and destination",
            "origin": {"lat": origin_lat, "lon": origin_lon},
            "destination": {"lat": dest_lat, "lon": dest_lon},
            "waypoints": [],
            "distance_km": 0.0,
            "distance_nm": 0.0,
            "estimated_time_hrs": 0.0,
            "grid_stats": grid.grid_stats,
        }

    path, total_km, nodes_explored = result

    # Convert path cells to waypoint coordinates
    waypoints = []
    for idx, (r, c) in enumerate(path):
        lat, lon = grid.get_coords(r, c)
        if idx == 0:
            label = "Departure (snapped)"
        elif idx == len(path) - 1:
            label = "Arrival (snapped)"
        else:
            label = f"Waypoint {idx}"
        waypoints.append({"lat": lat, "lon": lon, "label": label})

    distance_nm = total_km / KM_PER_NAUTICAL_MILE
    speed_kmh = vessel_speed_knots * KM_PER_NAUTICAL_MILE
    time_hrs = total_km / speed_kmh if speed_kmh > 0 else 0.0

    logger.info("A* route found: %d waypoints, %.2f km (%.2f nm), "
                "%.2f hrs at %.1f knots, %d nodes explored",
                len(waypoints), total_km, distance_nm,
                time_hrs, vessel_speed_knots, nodes_explored)

    return {
        "source": "A* over GEBCO 2020 bathymetry (OpenTopoData)",
        "origin": {"lat": origin_lat, "lon": origin_lon},
        "destination": {"lat": dest_lat, "lon": dest_lon},
        "vessel_draft_m": vessel_draft_m,
        "vessel_speed_knots": vessel_speed_knots,
        "waypoints": waypoints,
        "distance_km": round(total_km, 2),
        "distance_nm": round(distance_nm, 2),
        "estimated_time_hrs": round(time_hrs, 2),
        "nodes_explored": nodes_explored,
        "path_length": len(waypoints),
        "grid_stats": grid.grid_stats,
    }
