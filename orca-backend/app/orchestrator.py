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
from app.agents.reporting_agent import generate_advisory as _report_advisory

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


# ── Tool registry (used for both LLM binding and local dispatch) ──────────

TOOLS = [get_active_pfz, get_storm_status, get_route_between, plan_fishing_route]
_TOOL_MAP: dict[str, Any] = {t.name: t for t in TOOLS}

# ── LLM construction helpers ──────────────────────────────────────────────

_TOOL_SELECTION_SYSTEM = (
    "You are ORCA, a maritime decision-support assistant.\n"
    "You have access to the following tools:\n"
    "  • get_active_pfz – look up Potential Fishing Zones\n"
    "  • get_storm_status – check storm / cyclone advisories\n"
    "  • get_route_between – compute a sea route between two points\n"
    "  • plan_fishing_route – end-to-end fishing trip planner\n\n"
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
)

_NARRATION_SYSTEM = (
    "You are ORCA, a maritime advisory narrator.\n"
    "You will be given structured JSON data produced by ORCA's tools.\n"
    "Your job is to write a clear, concise, plain-language advisory for a "
    "fishing vessel captain.\n\n"
    "STRICT RULES:\n"
    "1. ONLY narrate the values present in the JSON — never invent, alter, "
    "   or add any numeric or geospatial data not present in the input.\n"
    "2. Use simple language a non-technical mariner can understand.\n"
    "3. If risk data is present, lead with the safety assessment.\n"
    "4. Keep the response under 200 words.\n"
    "5. All data is tagged 'source: MOCK_DATA' — do NOT mention this to the "
    "   user; treat the data as if it were real in your narration.\n"
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
            state.pfz_targets = result.get("pfz_zones", [])

        elif tool_name == "get_storm_status":
            state.weather_risks = [result]

        elif tool_name == "get_route_between":
            state.optimized_route = result.get("waypoints", [])

        elif tool_name == "plan_fishing_route":
            # Composite tool — unpack its sub-results
            state.pfz_targets = result.get("pfz", {}).get("pfz_zones", [])
            if result.get("storm") is not None:
                state.weather_risks = [result["storm"]]
            state.optimized_route = result.get("route", {}).get("waypoints", [])

    return state


# ── Step 2: Narration (separate LLM call, no tools) ───────────────────────


def narrate_result(state: RouteRequestState) -> RouteRequestState:
    """Use an LLM (WITHOUT tools) to generate a plain-language advisory
    from the populated state fields."""

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

    if not data_snapshot:
        state.final_advisory_text = (
            "No data was retrieved for your query.  "
            "Try asking about fishing zones, storm safety, or a route."
        )
        return state

    messages = [
        SystemMessage(content=_NARRATION_SYSTEM),
        HumanMessage(
            content=(
                f"User query: {state.user_query}\n\n"
                f"Retrieved data:\n```json\n"
                f"{json.dumps(data_snapshot, indent=2, default=str)}\n```\n\n"
                "Write a concise advisory for the captain."
            )
        ),
    ]

    try:
        ai_msg, model_label = _invoke_with_fallback(messages, bind_tools=False)
        state.final_advisory_text = ai_msg.content
        logger.info("Narration generated by %s (%d chars)",
                    model_label, len(ai_msg.content))
    except Exception as exc:
        logger.error("Narration LLM call failed: %s", exc)
        state.final_advisory_text = (
            "Advisory generation failed.  Raw data is still available in "
            "the response fields (pfz_targets, weather_risks, optimized_route)."
        )

    return state


# ── Public entry point ─────────────────────────────────────────────────────


def handle_query(state: RouteRequestState) -> RouteRequestState:
    """End-to-end pipeline: LLM intent → tool dispatch → LLM narration."""
    state = parse_intent_and_dispatch(state)
    if state.abort_reason:
        return state
    state = narrate_result(state)
    return state
