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

import time

def append_trace(state, stage: str, t_start: float, summary: str, source_type: str = "live"):
    duration = (time.time() - t_start) * 1000
    if not hasattr(state, "execution_trace") or state.execution_trace is None:
        state.execution_trace = []
    state.execution_trace.append({
        "stage": stage,
        "duration_ms": round(duration, 2),
        "summary": summary,
        "source_type": source_type
    })

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
def get_active_pfz(region_bbox: list[float], language_out: str = "en", target_time: str = "now") -> dict:
    """Return active Potential Fishing Zone (PFZ) advisories for a bounding box.

    Args:
        region_bbox: Four floats [south_lat, west_lon, north_lat, east_lon]
                     defining the search area.  Use [9.0, 79.0, 9.5, 79.8]
                     for the Rameswaram / Gulf of Mannar region.
        language_out: Language for the advisory output (e.g. "en", "ta", "hi").
        target_time: Target date/time reference (e.g. "now", "today", "tomorrow morning", "tomorrow evening").
    """
    return _pfz_get_active(region_bbox)


@tool
def get_storm_status(region_bbox: list[float], language_out: str = "en", target_time: str = "now") -> dict:
    """Check for active storms, cyclones, or severe-weather advisories in a region.

    Args:
        region_bbox: Four floats [south_lat, west_lon, north_lat, east_lon]
                     defining the area to check.  Use [9.0, 79.0, 9.5, 79.8]
                     for the Rameswaram / Gulf of Mannar region.
        language_out: Language for the advisory output (e.g. "en", "ta", "hi").
        target_time: Target date/time reference (e.g. "now", "today", "tomorrow morning", "tomorrow evening").
    """
    return _weather_get_storm(region_bbox, target_time)


@tool
def get_route_between(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    vessel_draft_m: float,
    language_out: str = "en",
    target_time: str = "now",
) -> dict:
    """Compute an optimised maritime route between two coordinates.

    Args:
        origin_lat:     Latitude of the departure point.
        origin_lon:     Longitude of the departure point.
        dest_lat:       Latitude of the destination.
        dest_lon:       Longitude of the destination.
        vessel_draft_m: Vessel draft in metres (for depth clearance).
        language_out:   Language for the advisory output (e.g. "en", "ta", "hi").
        target_time:    Target date/time reference (e.g. "now", "today", "tomorrow morning", "tomorrow evening").
    """
    return _geo_get_route(origin_lat, origin_lon, dest_lat, dest_lon, vessel_draft_m)


@tool
def plan_fishing_route(
    origin_port: str,
    check_storm_risk: bool,
    language_out: str = "en",
    target_time: str = "now",
) -> dict:
    """High-level fishing-trip planner.  Combines PFZ lookup, optional storm
    risk check, and route generation into a single advisory bundle.

    Args:
        origin_port:     Name of the departure port (e.g. "Rameswaram").
        check_storm_risk: Whether to include a storm-risk check.
        language_out:    Language for the advisory output (e.g. "en", "ta").
        target_time:     Target date/time reference (e.g. "now", "today", "tomorrow morning").
    """
    bbox = _DEFAULT_BBOX
    pfz = _pfz_get_active(bbox)
    storm: dict | None = None
    if check_storm_risk:
        storm = _weather_get_storm(bbox, target_time)

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
def get_ecosystem_trend(region: str, years: int = 3, language_out: str = "en", target_time: str = "now") -> dict:
    """Analyse multi-year ecosystem health trends (SST, chlorophyll-a, fish productivity)
    for a named coastal region.

    Args:
        region: Name of the coastal region (e.g. "Gulf of Mannar", "Rameswaram").
        years:  Number of years to analyse (default 3).
        language_out: Language for the advisory output (e.g. "en", "ta", "hi").
        target_time: Target date/time reference (e.g. "now", "today", "tomorrow morning").
    """
    return _marine_ecosystem(region, years)



@tool
def plan_commercial_route(origin_port: str, destination_port: str, vessel_draft_m: float = 3.0, language_out: str = "en", target_time: str = "now") -> dict:
    """High-level commercial/cargo/transit route planner.
    
    Args:
        origin_port: Name of the departure port (e.g. "Rameswaram").
        destination_port: Name of the destination port (e.g. "Pamban").
        vessel_draft_m: Vessel draft in meters.
        language_out: Language for the advisory output (e.g. "en", "ta", "hi").
        target_time: Target date/time reference (e.g. "now", "today", "tomorrow morning").
    """
    origin_coords = get_location_coordinates(origin_port)
    dest_coords = get_location_coordinates(destination_port)

    if not origin_coords or not dest_coords:
        return {
            "error": "Could not resolve origin or destination coordinates.",
            "origin_port": origin_port,
            "destination_port": destination_port,
        }

    return _geo_get_route(
        origin_lat=origin_coords[0],
        origin_lon=origin_coords[1],
        dest_lat=dest_coords[0],
        dest_lon=dest_coords[1],
        vessel_draft_m=vessel_draft_m,
        vessel_speed_knots=12.0,
        route_profile="commercial"
    )

TOOLS = [get_active_pfz, get_storm_status, get_route_between, plan_fishing_route, plan_commercial_route, get_ecosystem_trend]
_TOOL_MAP: dict[str, Any] = {t.name: t for t in TOOLS}

# ── LLM construction helpers ──────────────────────────────────────────────

_TOOL_SELECTION_SYSTEM = (
    "You are ORCA, a maritime decision-support assistant.\n"
    "You have access to the following tools:\n"
    "  • get_active_pfz – look up Potential Fishing Zones\n"
    "  • get_storm_status – check storm / cyclone advisories\n"
    "  • get_route_between – compute a sea route between two points\n"
    "  • plan_fishing_route – end-to-end fishing trip planner\n"
    "  • plan_commercial_route – commercial transit route planner\n"
    "  • get_ecosystem_trend – analyse multi-year ecosystem health trends "
    "(SST, chlorophyll-a, fish productivity)\n\n"
    "RULES:\n"
    "1. You MUST respond ONLY with one or more tool_calls.\n"
    "2. NEVER return coordinates, route waypoints, PFZ data, or weather data "
    "   directly in your text.  ALL geospatial / oceanographic data must come "
    "   from a tool call.\n"
    "3. If you cannot determine which tool to call, call get_storm_status with "
    "   region_bbox [9.0, 79.0, 9.5, 79.8] as a safe default.\n"
    "4. For fishing-related queries that mention safety, call plan_fishing_route with check_storm_risk=true.\n"
    "4b. For commercial, cargo, or transit routing queries (e.g. commercial route avoiding fishing zones), call plan_commercial_route.\n"
    "5. For queries only about storms or weather safety, call get_storm_status.\n"
    "6. For queries about fishing zones or PFZ, call get_active_pfz.\n"
    "7. For queries about routing, call get_route_between with appropriate "
    "   coordinates (use Rameswaram harbour 9.2885, 79.3129 as default origin).\n"
    "8. For queries about ecosystem health, fish productivity trends, SST changes, "
    "   chlorophyll decline, or 'why has fishing declined', call get_ecosystem_trend.\n"
    "9. MULTILINGUAL SUPPORT: You MUST auto-detect the language of the user's query and pass it as the `language_out` parameter in every tool call (e.g. 'ta' for Tamil, 'hi' for Hindi, 'en' for English).\n"
    "10. CONVERSATIONAL CONTEXT: For short follow-up queries (e.g. 'what about [Location]?', 'and tomorrow?'), you MUST inherit the intent and tool choice from the prior turns. If the previous question was about fishing safety, use the fishing safety tool for the new location/time.\n"
    "11. TARGET TIME: Extract any time references (e.g. 'today', 'tomorrow morning', 'tomorrow evening') and pass it to the tool as `target_time`. Default to 'now' if unspecified.\n"
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
    "   or add any numeric or geospatial data not present in the input. Explicitly forbidden: mentioning fish species or confidence percentages (this data does not exist in the real source).\n"\
    "4. If mpa_caution is true, clearly mention the route intersects the provided MPA/Sector name, using only the provided name without inventing regulatory language.\n"
    "5. When describing PFZ advisories, ALWAYS use the bearing/distance/depth guidance from the named landing centre provided in the data.\n"
    "6. Include real SST and Chlorophyll values when present ('sea surface temperature X°C, chlorophyll Y mg/m³ near [location]') without fabricating a value when the fetch returns null — in that case simply omit the SST/chlorophyll line.\n"
    "7. Use simple language a non-technical mariner can understand.\n"
    "8. Keep the response under 200 words.\n"
)


def _build_primary_llm():
    """Groq (qwen3.8-27b) — primary model."""
    from langchain_groq import ChatGroq

    return ChatGroq(model="qwen/qwen3.8-27b", temperature=0)


def _build_fallback_llm():
    """Google Gemini 3.6 Flash — fallback model."""
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
    mode_hint = getattr(state, "mode", "fishing")
    system_prompt = _TOOL_SELECTION_SYSTEM + f"\n\nACTIVE MODE HINT: {mode_hint.upper()}\n"
    messages: list = [SystemMessage(content=system_prompt)]
    from langchain_core.messages import AIMessage
    for msg in state.chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role in ("assistant", "ai"):
            messages.append(AIMessage(content=content))
        elif role == "system":
            messages.append(SystemMessage(content=content))
    messages.append(HumanMessage(content=state.user_query))

    # Call LLM with tool binding
    t0_intent = time.time()
    ai_msg, model_label = _invoke_with_fallback(messages, bind_tools=True)
    append_trace(state, "intent_parse", t0_intent, f"Parsed intent via {model_label}.", "llm")

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

        if "language_out" in tool_args:
            state.detected_language = tool_args.pop("language_out", "en")

        if tool_name not in _TOOL_MAP:
            logger.error("Unknown tool requested: %s", tool_name)
            continue

        t0_tool = time.time()
        try:
            result = _TOOL_MAP[tool_name].invoke(tool_args)
            
            # Direct read of source field
            source_type = "live"
            
            # Helper to search nested dicts for source strings
            import json
            result_str = json.dumps(result).upper()
            
            if "MOCK_DATA" in result_str:
                source_type = "mock"
            elif "LOCAL_FALLBACK_SNAPSHOT" in result_str:
                source_type = "fallback"
            
            summary = f"Executed {tool_name} successfully."
            if tool_name == "get_active_pfz":
                summary = f"Fetched {len(result.get('pfz_lines', []))} PFZ lines, source={source_type}"
            elif tool_name == "get_storm_status":
                summary = f"Fetched weather status, source={source_type}"
            elif tool_name in ["get_route_between", "plan_fishing_route", "plan_commercial_route"]:
                waypoints = result.get("waypoints", [])
                summary = f"Calculated route with {len(waypoints)} waypoints, source={source_type}"
                
            append_trace(state, f"tool_execution: {tool_name}", t0_tool, summary, source_type)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Tool execution failed: %s", exc)
            append_trace(state, f"tool_execution: {tool_name}", t0_tool, f"Tool failed: {exc}", "error")
            continue

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
            state.route_details = result

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
            state.route_details = result.get("route", {})

        elif tool_name == "plan_commercial_route":
            state.optimized_route = result.get("waypoints", [])
            state.route_details = result
            if not hasattr(state, '_extra_data'):
                state._extra_data = {}
            state._extra_data["commercial_advisory"] = result
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
                f"Write a concise advisory for the captain. State the exact verdict above and explain the rationale using the supporting data.\n"
                f"IMPORTANT: You MUST write the ENTIRE advisory in language code '{state.detected_language}' (detected from the user's query). Do not write in English unless the language code is 'en'."
            )
        ),
    ]

    try:
        t0_narrate = time.time()
        ai_msg, model_label = _invoke_with_fallback(messages, bind_tools=False)
        append_trace(state, "narration_generation", t0_narrate, f"Generated final advisory via {model_label}.", "llm")
        
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
    import re
    import requests
    import urllib.parse
    
    # Tier 1: Coordinate Regex
    coord_pattern = r'(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)'
    match = re.search(coord_pattern, query)
    if match:
        logger.info(f"Location resolved via Tier 1 (Regex): {match.groups()}")
        return float(match.group(1)), float(match.group(2))
    
    # Tier 2: Local Gazetteer
    query_lower = query.lower()
    gazetteer = {
        "rameswaram": (9.2885, 79.3129),
        "ராமேஸ்வரம்": (9.2885, 79.3129),
        "रामेश्वरम": (9.2885, 79.3129),
        "dhanushkodi": (9.1600, 79.4300),
        "தனுஷ்கோடி": (9.1600, 79.4300),
        "धनुषकोडी": (9.1600, 79.4300),
        "mandapam": (9.2783, 79.1235),
        "மண்டபம்": (9.2783, 79.1235),
        "मंडपम": (9.2783, 79.1235),
        "gulf of mannar": (9.25, 79.4),
        "மன்னார் வளைகுடா": (9.25, 79.4),
        "मन्नार की खाड़ी": (9.25, 79.4),
        "palk bay": (9.66, 79.28),
        "பாக் வளைகுடா": (9.66, 79.28),
        "पाक खाड़ी": (9.66, 79.28),
        "tuticorin": (8.7642, 78.1348),
        "thoothukudi": (8.7642, 78.1348),
        "தூத்துக்குடி": (8.7642, 78.1348),
        "तूतीकोरिन": (8.7642, 78.1348),
        "pamban": (9.2721, 79.2152),
        "பாம்பன்": (9.2721, 79.2152),
        "पंबन": (9.2721, 79.2152)
    }
    for place, coords in gazetteer.items():
        if place in query_lower:
            logger.info(f"Location resolved via Tier 2 (Gazetteer): {place} -> {coords}")
            return coords

    # Tier 3: Hardened Nominatim Fallback
    url = 'https://nominatim.openstreetmap.org/search?q=' + urllib.parse.quote(query) + '&format=json&limit=1'
    try:
        response = requests.get(
            url, 
            headers={'User-Agent': 'ORCA_Maritime_App/1.0'},
            timeout=1.5
        )
        response.raise_for_status()
        data = response.json()
        if data:
            logger.info(f"Location resolved via Tier 3 (Nominatim): {data[0]['lat']}, {data[0]['lon']}")
            return float(data[0]['lat']), float(data[0]['lon'])
    except requests.RequestException as e:
        logger.warning(f"Tier 3 Nominatim error or timeout: {e}")
        return None
        
    return None

def handle_query(state: RouteRequestState) -> RouteRequestState:
    """End-to-end pipeline: LLM intent -> tool dispatch -> deterministic verdict -> LLM narration."""
    
    # 0. Deterministic pre-LLM distress detection
    # NOTE: This is keyword-based detection only, in English, and does not yet cover regional-language distress phrases or voice input - this is a known, stated limitation, not a claimed complete safety net.
    DISTRESS_KEYWORDS = [
        "mayday", "sos", "sinking", "capsized", "capsizing", "man overboard", 
        "drowning", "taking water", "engine failure adrift", "distress", 
        "emergency", "help us", "boat sinking", "losing control"
    ]
    query_lower = state.user_query.lower()
    if any(kw in query_lower for kw in DISTRESS_KEYWORDS):
        logger.warning(f"Distress detected in query: '{state.user_query}'")
        
        bearing_guidance = ""
        try:
            # Try to quickly resolve location to give return bearing, but suppress failures
            coords = get_location_coordinates(state.user_query)
            if coords is not None:
                lat, lon = coords
                from app.agents.pfz_agent import get_nearest_landing_centre
                lc_info, _ = get_nearest_landing_centre(lat, lon)
                if lc_info and lc_info.get("LC_NAME"):
                    bearing = lc_info.get("BEARING", "?")
                    dist_km = lc_info.get("DISTANCE_F", "?")
                    bearing_guidance = f"\n\nBased on your location, the nearest registered landing centre is {lc_info['LC_NAME']} at bearing {bearing}° ({dist_km} km)."
        except Exception as e:
            logger.error(f"Error resolving location for distress guidance: {e}")

        state.status = "DISTRESS_DETECTED"
        state.verdict = None
        state.final_advisory_text = (
            "EMERGENCY DETECTED.\n\n"
            "This system is an advisory tool and has NO integration with telecom or local authorities. No emergency dispatch has been made.\n\n"
            "FOR IMMEDIATE ASSISTANCE, CALL:\n"
            "* Indian Coast Guard: 1554\n"
            "* National Emergency: 112"
            f"{bearing_guidance}"
        )
        return state

    # 1. Out-of-bounds / invalid location validation
    coords = get_location_coordinates(state.user_query)
    
    if coords is None:
        # If no coordinates could be resolved at all, also fail closed
        state.verdict = None
        state.status = "OUT_OF_BOUNDS"
        state.final_advisory_text = "This location could not be resolved or is outside ORCA's current operational area (Gulf of Mannar / Palk Bay, Tamil Nadu). This demo is scoped to this region and cannot provide marine safety data elsewhere."
        return state
        
    lat, lon = coords
    # Box: lat 9.0–9.5, lon 79.0–79.8, plus 0.5 margin -> lat 8.5 to 10.0, lon 78.5 to 80.3
    if not (8.5 <= lat <= 10.0 and 78.5 <= lon <= 80.3):
        logger.warning(f"Query out of bounds: {coords} for '{state.user_query}'")
        state.verdict = None
        state.status = "OUT_OF_BOUNDS"
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
    route_data = state.route_details

    t0_verdict = time.time()
    verdict_result = evaluate_verdict(
        weather_result=weather_data,
        pfz_result=pfz_data,
        route_result=route_data,
    )
    append_trace(state, "verdict_evaluation", t0_verdict, f"Evaluated verdict: {verdict_result['verdict']}", "live" if not verdict_result.get('fallback_used') else "fallback")
    state.verdict = verdict_result
    logger.info("DETERMINISTIC VERDICT: %s | Reason: %s",
                verdict_result["verdict"], verdict_result["reason"])

    state = narrate_result(state)
    return state
