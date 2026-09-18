"""ORCA Orchestrator — LLM-driven tool selection with Groq primary / Gemini fallback.

Architecture
────────────
1.  parse_intent_and_dispatch()  — LLM **with tools bound** selects which
    tool(s) to call.  The model is never allowed to fabricate geospatial data
    in its own text; it must always emit a tool_call.
2.  narrate_result()             — A *separate* LLM call **without tools**
    generates a plain-language advisory from the populated state.
These two steps are intentionally separate (core architectural requirement).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.schemas import RouteRequestState

# ── Agent mock implementations (unchanged) ─────────────────────────────────
from app.agents.weather_agent import get_storm_status as _weather_get_storm
from app.agents.pfz_agent import get_active_pfz as _pfz_get_active
from app.agents.geospatial_agent import get_route_between as _geo_get_route
from app.agents.risk_agent import evaluate_verdict
from app.agents.reporting_agent import generate_advisory as _report_advisory
from app.agents.marine_data_agent import analyze_ecosystem_trends as _marine_ecosystem

load_dotenv()

logger = logging.getLogger("orca.orchestrator")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
)

# ---------------------------------------------------------------------------
# Default bounding box centred on Rameswaram, Tamil Nadu
# [south, west, north, east]
# ---------------------------------------------------------------------------
_DEFAULT_BBOX: list[float] = [9.0, 79.0, 9.5, 79.8]

# Placeholder origin (Rameswaram harbour) and destination (first PFZ centroid)
_PLACEHOLDER_ORIGIN = (9.2885, 79.3129)
_PLACEHOLDER_DEST = (9.35, 79.45)
_PLACEHOLDER_DRAFT_M = 2.5


# ── @tool-decorated wrappers (delegate to existing agent stubs) ────────────


@tool
def get_active_pfz(region_bbox: list[float]) -> dict:
    """Return active Potential Fishing Zone (PFZ) advisories for a bounding box.

    Args:
        region_bbox: Four floats [south_lat, west_lon, north_lat, east_lon]
                     defining the search area.  Use [9.0, 79.0, 9.5, 79.8]
                     for the Rameswaram / Gulf of Mannar region.
    """
    return _pfz_get_active(region_bbox)


@tool
def get_storm_status(region_bbox: list[float]) -> dict:
    """Check for active storms, cyclones, or severe-weather advisories in a region.

    Args:
        region_bbox: Four floats [south_lat, west_lon, north_lat, east_lon]
                     defining the area to check.  Use [9.0, 79.0, 9.5, 79.8]
                     for the Rameswaram / Gulf of Mannar region.
    """
    return _weather_get_storm(region_bbox)


@tool
def get_route_between(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    vessel_draft_m: float,
) -> dict:
    """Compute an optimised maritime route between two coordinates.

    Args:
        origin_lat:     Latitude of the departure point.
        origin_lon:     Longitude of the departure point.
        dest_lat:       Latitude of the destination.
        dest_lon:       Longitude of the destination.
        vessel_draft_m: Vessel draft in metres (for depth clearance).
    """
    return _geo_get_route(origin_lat, origin_lon, dest_lat, dest_lon, vessel_draft_m)


@tool
def plan_fishing_route(
    origin_port: str,
    check_storm_risk: bool,
    language_out: str,
) -> dict:
    """High-level fishing-trip planner.  Combines PFZ lookup, optional storm
    risk check, and route generation into a single advisory bundle.

    Args:
        origin_port:     Name of the departure port (e.g. "Rameswaram").
        check_storm_risk: Whether to include a storm-risk check.
        language_out:    Language for the advisory output (e.g. "en", "ta").
    """
    bbox = _DEFAULT_BBOX
    pfz = _pfz_get_active(bbox)
    storm: dict | None = None
    if check_storm_risk:
        storm = _weather_get_storm(bbox)

    pfz_lines = pfz.get("pfz_lines", [])
    if pfz_lines:
        from shapely.geometry import Point, MultiLineString
        from shapely.ops import nearest_points
        import json

        first_pfz = pfz_lines[0]
        geom = first_pfz.get("geometry", {})
        
        origin_lon, origin_lat = _PLACEHOLDER_ORIGIN[1], _PLACEHOLDER_ORIGIN[0]
        target_lat, target_lon = _PLACEHOLDER_DEST[0], _PLACEHOLDER_DEST[1]
        
        if geom.get("type") == "MultiLineString" and geom.get("coordinates"):
            try:
                mls = MultiLineString(geom["coordinates"])
                origin_point = Point(origin_lon, origin_lat)
                
                # Shapely returns (geom_from_p1, geom_from_p2)
                # We want the point on the MultiLineString (which is arg 2)
                _, nearest_geom = nearest_points(origin_point, mls)
                target_lat, target_lon = nearest_geom.y, nearest_geom.x
                
                old_lon, old_lat = geom["coordinates"][0][0][0], geom["coordinates"][0][0][1]
                logger.info(f"Nearest-point fix -> Old: ({old_lat:.4f}, {old_lon:.4f}) | New: ({target_lat:.4f}, {target_lon:.4f})")
            except Exception as e:
                logger.error(f"Shapely nearest point failed: {e}")
        
        dest_lat, dest_lon = target_lat, target_lon
    else:
        dest_lat, dest_lon = _PLACEHOLDER_DEST[0], _PLACEHOLDER_DEST[1]
        
    route = _geo_get_route(
        origin_lat=_PLACEHOLDER_ORIGIN[0],
        origin_lon=_PLACEHOLDER_ORIGIN[1],
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        vessel_draft_m=_PLACEHOLDER_DRAFT_M,
    )

    return {
        "source": "INCOIS GeoServer",
        "origin_port": origin_port,
        "language": language_out,
        "pfz": pfz,
        "storm": storm,
        "route": route,
    }


# ── Tool registry (used for both LLM binding and local dispatch) ──────────

@tool
def get_ecosystem_trend(region: str, years: int = 3) -> dict:
    """Analyse multi-year ecosystem health trends (SST, chlorophyll-a, fish productivity)
    for a named coastal region.

    Args:
        region: Name of the coastal region (e.g. "Gulf of Mannar", "Rameswaram").
        years:  Number of years to analyse (default 3).
    """
    return _marine_ecosystem(region, years)


TOOLS = [get_active_pfz, get_storm_status, get_route_between, plan_fishing_route, get_ecosystem_trend]
_TOOL_MAP: dict[str, Any] = {t.name: t for t in TOOLS}

# ── LLM construction helpers ──────────────────────────────────────────────

_TOOL_SELECTION_SYSTEM = (
    "You are ORCA, a maritime decision-support assistant.\n"
    "You have access to the following tools:\n"
    "  • get_active_pfz – look up Potential Fishing Zones\n"
    "  • get_storm_status – check storm / cyclone advisories\n"
    "  • get_route_between – compute a sea route between two points\n"
    "  • plan_fishing_route – end-to-end fishing trip planner\n"
    "  • get_ecosystem_trend – analyse multi-year ecosystem health trends "
    "(SST, chlorophyll-a, fish productivity)\n\n"
    "RULES:\n"
    "1. You MUST respond ONLY with one or more tool_calls.\n"
    "2. NEVER return coordinates, route waypoints, PFZ data, or weather data "
    "   directly in your text.  ALL geospatial / oceanographic data must come "
    "   from a tool call.\n"
    "3. If you cannot determine which tool to call, call get_storm_status with "
    "   region_bbox [9.0, 79.0, 9.5, 79.8] as a safe default.\n"
    "4. For fishing-related queries that mention safety, call plan_fishing_route "
    "   with check_storm_risk=true.\n"
    "5. For queries only about storms or weather safety, call get_storm_status.\n"
    "6. For queries about fishing zones or PFZ, call get_active_pfz.\n"
    "7. For queries about routing, call get_route_between with appropriate "
    "   coordinates (use Rameswaram harbour 9.2885, 79.3129 as default origin).\n"
    "8. For queries about ecosystem health, fish productivity trends, SST changes, "
    "   chlorophyll decline, or 'why has fishing declined', call get_ecosystem_trend.\n"
)

_NARRATION_SYSTEM = (
    "You are ORCA, a maritime advisory narrator.\n"
    "You are given a pre-computed verdict (SAFE, CAUTION, or NO-GO) and its reason. "
    "You must state this exact verdict in your response — you are NOT permitted to soften, "
    "upgrade, downgrade, or reinterpret it. Your only job is to explain the verdict in plain "
    "language using the supporting data provided.\n\n"
    "STRICT RULES:\n"
    "1. State the exact pre-computed verdict (SAFE, CAUTION, or NO-GO) prominently at the beginning.\n"
    "2. You are NOT permitted to decide or alter the safety verdict on your own.\n"
    "3. ONLY narrate the values present in the JSON — never invent, alter, "
    "   or add any numeric or geospatial data not present in the input. Explicitly forbidden: mentioning fish species or confidence percentages (this data does not exist in the real source).\n"
    "4. When describing PFZ advisories, ALWAYS use the bearing/distance/depth guidance from the named landing centre provided in the data.\n"
    "5. Include real SST and Chlorophyll values when present ('sea surface temperature X°C, chlorophyll Y mg/m³ near [location]') without fabricating a value when the fetch returns null — in that case simply omit the SST/chlorophyll line.\n"
    "6. Use simple language a non-technical mariner can understand.\n"
    "7. Keep the response under 200 words.\n"
)


def _build_primary_llm():
    """Groq (llama-3.3-70b-versatile) — primary model."""
    from langchain_groq import ChatGroq

    return ChatGroq(model="qwen/qwen3.8-27b", temperature=0)


def _build_fallback_llm():
    """Google Gemini 2.0 Flash — fallback model."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)


def _invoke_with_fallback(messages, *, bind_tools: bool) -> tuple[Any, str]:
    """Try Groq first; on any exception fall back to Gemini.

    Returns (ai_message, model_used_label).
    """
    for label, builder in [("groq/qwen3.8-27b", _build_primary_llm),
                           ("gemini/gemini-3.6-flash", _build_fallback_llm)]:
        try:
            llm = builder()
            if bind_tools:
                llm = llm.bind_tools(TOOLS)
            response = llm.invoke(messages)
            logger.info("LLM call succeeded with model=%s", label)
            return response, label
        except Exception as exc:
            logger.warning("Model %s failed (%s: %s), trying fallback…",
                           label, type(exc).__name__, exc)
            continue

    raise RuntimeError("All LLM providers failed.")


# ── Step 1: LLM-driven intent parsing & tool dispatch ─────────────────────


def parse_intent_and_dispatch(state: RouteRequestState) -> RouteRequestState:
    """Use an LLM (with tools bound) to decide which tool(s) to call,
    then execute them and populate the state."""

    # Build message list
    messages: list = [SystemMessage(content=_TOOL_SELECTION_SYSTEM)]
    for msg in state.chat_history:
        role = msg.get("role", "user")
        if role == "user":
            messages.append(HumanMessage(content=msg.get("content", "")))
    messages.append(HumanMessage(content=state.user_query))

    # Call LLM with tool binding
    ai_msg, model_label = _invoke_with_fallback(messages, bind_tools=True)

    tool_calls = ai_msg.tool_calls if hasattr(ai_msg, "tool_calls") else []

    if not tool_calls:
        logger.warning("LLM returned no tool calls — aborting.")
        state.abort_reason = (
            f"The LLM ({model_label}) did not select any tool. "
            "It may not have understood the query."
        )
        return state

    # Execute each selected tool
    for tc in tool_calls:
        tool_name = tc["name"]
        tool_args = tc["args"]
        logger.info("Tool selected by %s: %s(%s)", model_label, tool_name, tool_args)

        if tool_name not in _TOOL_MAP:
            logger.error("Unknown tool requested: %s", tool_name)
            continue

        result = _TOOL_MAP[tool_name].invoke(tool_args)

        # ── Populate state based on which tool was called ──────────────
        if tool_name == "get_active_pfz":
            state.pfz_targets = result.get("pfz_lines", [])
            if not hasattr(state, '_extra_data'):
                state._extra_data = {}
            state._extra_data["pfz_info"] = {
                "sector": result.get("sector"),
                "advisory_date": result.get("advisory_date"),
                "nearest_landing_centre": result.get("nearest_landing_centre"),
                "sst_celsius": result.get("sst_celsius"),
                "chlorophyll_mgm3": result.get("chlorophyll_mgm3"),
                "source": result.get("source")
            }

        elif tool_name == "get_storm_status":
            state.weather_risks = [result]

        elif tool_name == "get_route_between":
            state.optimized_route = result.get("waypoints", [])

        elif tool_name == "plan_fishing_route":
            # Composite tool — unpack its sub-results
            pfz_res = result.get("pfz", {})
            state.pfz_targets = pfz_res.get("pfz_lines", [])
            if not hasattr(state, '_extra_data'):
                state._extra_data = {}
            state._extra_data["pfz_info"] = {
                "sector": pfz_res.get("sector"),
                "advisory_date": pfz_res.get("advisory_date"),
                "nearest_landing_centre": pfz_res.get("nearest_landing_centre"),
                "sst_celsius": pfz_res.get("sst_celsius"),
                "chlorophyll_mgm3": pfz_res.get("chlorophyll_mgm3"),
                "source": pfz_res.get("source")
            }
            if result.get("storm") is not None:
                state.weather_risks = [result["storm"]]
            state.optimized_route = result.get("route", {}).get("waypoints", [])

        elif tool_name == "get_ecosystem_trend":
            # Store ecosystem trend data in the state for narration
            # (no separate state field yet — pass via weather_risks or a generic bucket)
            if not hasattr(state, '_extra_data'):
                state._extra_data = {}
            state._extra_data["ecosystem_trend"] = result

    return state


# ── Step 2: Narration (separate LLM call, no tools) ───────────────────────


def narrate_result(state: RouteRequestState) -> RouteRequestState:
    """Use an LLM (WITHOUT tools) to generate a plain-language advisory
    from the populated state fields and deterministic verdict."""

    # Build a data snapshot for the narrator
    data_snapshot: dict[str, Any] = {}
    if state.pfz_targets:
        data_snapshot["pfz_targets"] = state.pfz_targets
    if state.weather_risks:
        data_snapshot["weather_risks"] = state.weather_risks
    if state.optimized_route:
        data_snapshot["optimized_route"] = state.optimized_route
    if state.abort_reason:
        data_snapshot["abort_reason"] = state.abort_reason
    if hasattr(state, '_extra_data') and state._extra_data:
        data_snapshot.update(state._extra_data)

    verdict_info = state.verdict or {
        "verdict": "CAUTION",
        "reason": "No verdict was evaluated.",
        "evaluated_at": "",
    }

    messages = [
        SystemMessage(content=_NARRATION_SYSTEM),
        HumanMessage(
            content=(
                f"User query: {state.user_query}\n\n"
                f"PRE-COMPUTED DETERMINISTIC VERDICT (MANDATORY TO RELAY AS-IS):\n"
                f"```json\n{json.dumps(verdict_info, indent=2)}\n```\n\n"
                f"SUPPORTING MARITIME DATA:\n"
                f"```json\n{json.dumps(data_snapshot, indent=2, default=str)}\n```\n\n"
                "Write a concise advisory for the captain. State the exact verdict above and explain the rationale using the supporting data."
            )
        ),
    ]

    try:
        ai_msg, model_label = _invoke_with_fallback(messages, bind_tools=False)
        
        content = ai_msg.content
        if isinstance(content, list):
            # Extract text from Gemini blocks
            text_parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
            content = "".join(text_parts) if text_parts else str(content)
            
        state.final_advisory_text = str(content)
        logger.info("Narration generated by %s (%d chars)",
                    model_label, len(state.final_advisory_text))
    except Exception as exc:
        logger.error("Narration LLM call failed: %s", exc)
        state.final_advisory_text = (
            f"Advisory Verdict: {verdict_info.get('verdict')} — {verdict_info.get('reason')}"
        )

    return state


# ── Public entry point ─────────────────────────────────────────────────────


def get_location_coordinates(query: str) -> tuple[float, float] | None:
    """Extract location from query and geocode via Nominatim."""
    from langchain_core.messages import SystemMessage, HumanMessage
    import urllib.request
    import urllib.parse
    messages = [
        SystemMessage(content="Extract the geographic location name (city, port, region) from the query. Return ONLY the location name. If none, return NONE."),
        HumanMessage(content=query)
    ]
    try:
        ai, _ = _invoke_with_fallback(messages, bind_tools=False)
        
        # Handle list format from Gemini
        content = ai.content
        if isinstance(content, list):
            text_parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
            place = "".join(text_parts).strip()
        else:
            place = str(content).strip()
            
        if place.upper() == 'NONE' or not place:
            return None
            
        place_lower = place.lower()
        if "gulf of mannar" in place_lower or "palk bay" in place_lower:
            return (9.25, 79.4) # Central valid point
        
        url = 'https://nominatim.openstreetmap.org/search?q=' + urllib.parse.quote(place) + '&format=json&limit=1'
        req = urllib.request.Request(url, headers={'User-Agent': 'ORCA_Maritime_App/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        logger.warning(f"Failed to geocode query location: {e}")
    return None


def handle_query(state: RouteRequestState) -> RouteRequestState:
    """End-to-end pipeline: LLM intent → tool dispatch → deterministic verdict → LLM narration."""
    # 1. Out-of-bounds / invalid location validation
    coords = get_location_coordinates(state.user_query)
    if coords is not None:
        lat, lon = coords
        # Box: lat 9.0–9.5, lon 79.0–79.8, plus 0.5 margin -> lat 8.5 to 10.0, lon 78.5 to 80.3
        if not (8.5 <= lat <= 10.0 and 78.5 <= lon <= 80.3):
            logger.warning(f"Query out of bounds: {coords} for '{state.user_query}'")
            state.verdict = None
            state.final_advisory_text = "This location is outside ORCA's current operational area (Gulf of Mannar / Palk Bay, Tamil Nadu). This demo is scoped to this region and cannot provide marine safety data elsewhere."
            return state

    state = parse_intent_and_dispatch(state)
    if state.abort_reason:
        return state

    # Deterministic verdict evaluation
    weather_data = state.weather_risks[0] if state.weather_risks else None
    if weather_data is None:
        bbox = list(state.bounding_box) if state.bounding_box else _DEFAULT_BBOX
        weather_data = get_storm_status.invoke({"region_bbox": bbox})
        state.weather_risks = [weather_data]

    pfz_data = {"pfz_zones": state.pfz_targets} if state.pfz_targets else None
    route_data = {"waypoints": state.optimized_route} if state.optimized_route else None

    verdict_result = evaluate_verdict(
        weather_result=weather_data,
        pfz_result=pfz_data,
        route_result=route_data,
    )
    state.verdict = verdict_result
    logger.info("DETERMINISTIC VERDICT: %s | Reason: %s",
                verdict_result["verdict"], verdict_result["reason"])
    print(f"[VERDICT EVALUATED] {json.dumps(verdict_result)}")

    state = narrate_result(state)
    return state
