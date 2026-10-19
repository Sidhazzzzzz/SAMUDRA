"""ORCA — Maritime Decision-Support System (FastAPI entrypoint)."""

from __future__ import annotations

import logging
import traceback

from fastapi import FastAPI, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.schemas import RouteRequestState
from app.orchestrator import handle_query
from app.agents.reporting_agent import generate_pdf_advisory
from app.cache import with_cache
from app.layer_proxy import proxy_layer_request

app = FastAPI(
    title="ORCA — Maritime Decision-Support System",
    version="1.0.0",
    description="Agentic backend for fishing-route planning, PFZ lookup, and storm advisories.",
)

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

logger = logging.getLogger("orca.main")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Last-resort safety net — catches any unhandled exception and returns
    a structured JSON error.  Never exposes raw stack traces to clients."""
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method, request.url.path, exc, exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "error_type": type(exc).__name__,
            "message": "An internal error occurred. The SAMUDRA team has been notified.",
            "path": str(request.url.path),
        },
    )



# ── Request body for /query ────────────────────────────────────────────────
class BroadcastRequest(BaseModel):
    polygon_coordinates: list[list[float]]
    event_type: str = "Severe Weather"
    severity: str = "Severe"
    urgency: str = "Immediate"
    certainty: str = "Observed"
    headline: str = "Hazardous Marine Conditions"
    description: str = "Evacuate the designated zone immediately."

class QueryRequest(BaseModel):
    user_query: str
    mode: str = "fishing"
    chat_history: list[dict] = []


# ── Endpoints ──────────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/system/status")
@with_cache(ttl=30)
async def system_status():
    """Check live reachability of every external dependency in one call."""
    import asyncio
    import os
    import httpx as _httpx

    checks: dict = {}

    async def probe(name: str, url: str, timeout: float = 5.0):
        try:
            async with _httpx.AsyncClient(timeout=timeout, verify=False) as client:
                resp = await client.get(
                    url, headers={"User-Agent": "SAMUDRA-Maritime-Advisory/1.0 (contact: sidharthakedlayah@gmail.com)"}
                )
                is_ok = resp.status_code == 200
                checks[name] = {"reachable": is_ok, "status_code": resp.status_code}
                if resp.status_code == 429:
                    checks[name]["rate_limited"] = True
                    checks[name]["fallback_active"] = True
                elif resp.status_code == 403:
                    checks[name]["forbidden"] = True
                    checks[name]["fallback_active"] = True
        except Exception as e:
            checks[name] = {"reachable": False, "error": f"{type(e).__name__}: {e}", "fallback_active": True}

    await asyncio.gather(
        probe("incois_wfs", "https://incois.gov.in/geoserver/PFZ_Automation/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_Automation:pfzlines&outputFormat=application/json&maxFeatures=1"),
        probe("incois_erddap", "https://erddap.incois.gov.in/erddap/version", 5.0),
        probe(
            "open_meteo_marine",
            "https://marine-api.open-meteo.com/v1/marine?latitude=9.25&longitude=79.4&current=wave_height",
        ),
        probe(
            "open_meteo_weather",
            "https://api.open-meteo.com/v1/forecast?latitude=9.25&longitude=79.4&current=wind_speed_10m",
        ),
        probe(
            "opentopodata",
            "https://api.opentopodata.org/v1/gebco2020?locations=9.25,79.4",
        ),
        probe(
            "nominatim",
            "https://nominatim.openstreetmap.org/search?q=Rameswaram&format=json&limit=1",
        ),
        probe("noaa_erddap_coastwatch", "https://coastwatch.pfeg.noaa.gov/erddap/version", 8.0),
        probe("noaa_erddap_upwell", "https://upwell.pfeg.noaa.gov/erddap/version", 8.0),
        probe("noaa_erddap_polarwatch", "https://polarwatch.noaa.gov/erddap/version", 8.0),
    )

    # LLM API keys — presence check only (no billing)
    checks["groq_api_key"] = {"configured": bool(os.getenv("GROQ_API_KEY"))}
    checks["gemini_api_key"] = {"configured": bool(os.getenv("GOOGLE_API_KEY"))}

    # Optional / mirrored services with guaranteed local offline fallbacks
    OPTIONAL_CHECKS = {
        "noaa_erddap_coastwatch", 
        "noaa_erddap_upwell",
        "nominatim",
        "incois_erddap",
    }

    all_ok = all(
        c.get("reachable", c.get("configured", False)) or c.get("fallback_active", False)
        for name, c in checks.items()
        if name not in OPTIONAL_CHECKS
    )

    # Tag optional checks in the response so callers know they don't affect the verdict
    for name in OPTIONAL_CHECKS:
        if name in checks:
            checks[name]["optional"] = True

    return {
        "status": "all_ok" if all_ok else "degraded",
        "checks": checks,
        "fallbacks": {
            "pfz": "pfz_fallback_snapshot.json",
            "weather": "weather_fallback_snapshot.json",
            "ecosystem": "ecosystem_fallback_snapshot.json",
            "geocoding": "local_gazetteer (Tamil/Hindi/English)",
            "layers": "fastapi_layer_proxy_with_offline_tiles"
        }
    }


@app.get("/api/layers/{layer_path:path}")
async def get_layer(layer_path: str, request: Request):
    """Proxy INCOIS WMS and WFS layers with disk caching and fallback snapshots."""
    return await proxy_layer_request(layer_path, request)


import time
import re

_QUERY_CACHE = {}

@app.post("/query")
async def query(body: QueryRequest) -> RouteRequestState:
    # Normalize query: lowercase, strip punctuation
    normalized_q = re.sub(r'[^a-z0-9]', '', body.user_query.lower())
    cache_key = f"{normalized_q}_{body.mode}"
    now = time.time()
    
    # Check cache (300s TTL)
    if cache_key in _QUERY_CACHE and (now - _QUERY_CACHE[cache_key]['time'] < 300):
        cached_state = _QUERY_CACHE[cache_key]['data'].copy(deep=True)
        if cached_state.final_advisory_text and " (Source: Cache)" not in cached_state.final_advisory_text:
            cached_state.final_advisory_text += "\n\n*(Source: Cache)*"
        return cached_state

    state = RouteRequestState(
        user_query=body.user_query,
        mode=body.mode,
        chat_history=body.chat_history,
    )
    result = handle_query(state)
    
    # Store in cache
    _QUERY_CACHE[cache_key] = {'time': now, 'data': result.copy(deep=True)}
    return result

@app.post("/export-pdf")
async def export_pdf(body: dict):
    pdf_bytes = generate_pdf_advisory(body)
    return Response(content=pdf_bytes, media_type="application/pdf")


@app.get("/risk-field")
def get_risk_field(origin_lat: float | None = Query(None), origin_lon: float | None = Query(None)):
    from app.agents.routing_engine import _get_nav_grid
    grid = _get_nav_grid()
    start_cell = None
    if origin_lat is not None and origin_lon is not None:
        start_cell = grid.snap_to_nearest_valid(origin_lat, origin_lon)
    field = grid.generate_risk_field(start_cell)
    return {"status": "success", "grid": field}

# Coastal Authority Endpoints

@app.post("/coastal-authority/broadcast")
def broadcast_alert(req: BroadcastRequest):
    """
    Checks which simulated vessels fall inside the polygon and generates a CAP 1.2 XML alert.
    NOTE: Simulated endpoint, no external dispatch.
    """
    from app.agents.coastal_authority_agent import check_vessels_in_zone, generate_cap_alert
    
    affected = check_vessels_in_zone(req.polygon_coordinates)
    cap_xml = generate_cap_alert(
        req.event_type, req.severity, req.urgency, req.certainty,
        req.headline, req.description, req.polygon_coordinates
    )
    
    return {
        "status": "success",
        "affected_vessels": affected,
        "cap_xml": cap_xml
    }

@app.get("/coastal-authority/block-rankings")
def get_block_rankings():
    """Returns coastal blocks ranked by real HMI risk scores."""
    from app.agents.coastal_authority_agent import get_coastal_block_rankings
    rankings = get_coastal_block_rankings()
    return {"status": "success", "rankings": rankings}
