"""ORCA Orchestrator — keyword-based intent dispatch to agent tool stubs.

This module defines the closed function-calling contract.  Every public
function either accepts structured parameters or returns deterministic
mock data.  No raw coordinates are passed that weren't produced by a
deterministic tool.
"""

from __future__ import annotations

from app.schemas import RouteRequestState
from app.agents.weather_agent import get_storm_status as _weather_get_storm
from app.agents.pfz_agent import get_active_pfz as _pfz_get_active
from app.agents.geospatial_agent import get_route_between as _geo_get_route
from app.agents.reporting_agent import generate_advisory as _report_advisory

# ---------------------------------------------------------------------------
# Default bounding box centred on Rameswaram, Tamil Nadu
# [south, west, north, east]
# ---------------------------------------------------------------------------
_DEFAULT_BBOX: list[float] = [9.0, 79.0, 9.5, 79.8]

# Placeholder origin (Rameswaram harbour) and destination (first PFZ centroid)
_PLACEHOLDER_ORIGIN = (9.2885, 79.3129)
_PLACEHOLDER_DEST = (9.35, 79.45)
_PLACEHOLDER_DRAFT_M = 2.5


# ── Closed tool functions ─────────────────────────────────────────────────


def plan_fishing_route(
    origin_port: str,
    check_storm_risk: bool,
    language_out: str,
) -> dict:
    """High-level planner — combines PFZ lookup, optional storm check, and
    route generation into a single advisory bundle."""
    bbox = _DEFAULT_BBOX
    pfz = _pfz_get_active(bbox)
    storm: dict | None = None
    if check_storm_risk:
        storm = _weather_get_storm(bbox)

    first_pfz = pfz["pfz_zones"][0]
    route = _geo_get_route(
        origin_lat=_PLACEHOLDER_ORIGIN[0],
        origin_lon=_PLACEHOLDER_ORIGIN[1],
        dest_lat=first_pfz["centroid_lat"],
        dest_lon=first_pfz["centroid_lon"],
        vessel_draft_m=_PLACEHOLDER_DRAFT_M,
    )

    return {
        "source": "MOCK_DATA",
        "origin_port": origin_port,
        "language": language_out,
        "pfz": pfz,
        "storm": storm,
        "route": route,
    }


def get_route_between(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    vessel_draft_m: float,
) -> dict:
    """Deterministic route between two points (delegates to geospatial agent)."""
    return _geo_get_route(origin_lat, origin_lon, dest_lat, dest_lon, vessel_draft_m)


def get_storm_status(region_bbox: list[float]) -> dict:
    """Storm / cyclone status for a region (delegates to weather agent)."""
    return _weather_get_storm(region_bbox)


def get_active_pfz(region_bbox: list[float]) -> dict:
    """Active PFZ advisories for a region (delegates to PFZ agent)."""
    return _pfz_get_active(region_bbox)


# ── Query handler ──────────────────────────────────────────────────────────


def handle_query(state: RouteRequestState) -> RouteRequestState:
    """Simple keyword-based intent dispatcher (no LLM call).

    Populates the relevant state fields with mock data and writes a
    plain-text advisory summary.
    """
    query_lower = state.user_query.lower()
    bbox = list(state.bounding_box) if state.bounding_box else _DEFAULT_BBOX
    summaries: list[str] = []

    # ── Intent: fishing / PFZ ──────────────────────────────────────────
    if "fish" in query_lower or "pfz" in query_lower:
        pfz_result = get_active_pfz(bbox)
        state.pfz_targets = pfz_result.get("pfz_zones", [])
        summaries.append(
            f"Found {pfz_result['pfz_count']} Potential Fishing Zones near Rameswaram."
        )

    # ── Intent: safety / storm ─────────────────────────────────────────
    if "safe" in query_lower or "storm" in query_lower:
        storm_result = get_storm_status(bbox)
        state.weather_risks = [storm_result]
        if storm_result["active"]:
            summaries.append("⚠ Active storm warning detected in the region!")
        else:
            summaries.append("No active storm warnings — conditions appear safe.")

    # ── Intent: route ──────────────────────────────────────────────────
    if "route" in query_lower:
        route_result = get_route_between(
            origin_lat=_PLACEHOLDER_ORIGIN[0],
            origin_lon=_PLACEHOLDER_ORIGIN[1],
            dest_lat=_PLACEHOLDER_DEST[0],
            dest_lon=_PLACEHOLDER_DEST[1],
            vessel_draft_m=_PLACEHOLDER_DRAFT_M,
        )
        state.optimized_route = route_result.get("waypoints", [])
        summaries.append(
            f"Route computed: {route_result['distance_nm']} NM, "
            f"~{route_result['estimated_time_hrs']} hrs."
        )

    # ── Fallback ───────────────────────────────────────────────────────
    if not summaries:
        summaries.append(
            "I couldn't determine a specific intent from your query. "
            "Try asking about fishing zones, storm safety, or a route."
        )

    state.final_advisory_text = " | ".join(summaries)
    return state
