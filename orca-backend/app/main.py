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

app = FastAPI(
    title="ORCA — Maritime Decision-Support System",
    version="0.1.0",
    description="Agentic backend for fishing-route planning, PFZ lookup, and storm advisories.",
)

# Allow CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
            "message": "An internal error occurred. The ORCA team has been notified.",
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
async def system_status():
    """Check live reachability of every external dependency in one call."""
    import asyncio
    import os
    import httpx as _httpx

    checks: dict = {}

    async def probe(name: str, url: str, timeout: float = 5.0):
        try:
            async with _httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(
                    url, headers={"User-Agent": "ORCA_Maritime_App/1.0"}
                )
                checks[name] = {"reachable": True, "status_code": resp.status_code}
        except Exception as e:
            checks[name] = {"reachable": False, "error": f"{type(e).__name__}: {e}"}

    await asyncio.gather(
        probe("incois_wfs", "https://incois.gov.in/geoserver/web/"),
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

    all_ok = all(
        c.get("reachable", c.get("configured", False)) for c in checks.values()
    )

    return {"status": "all_ok" if all_ok else "degraded", "checks": checks}


@app.post("/query")
async def query(body: QueryRequest) -> RouteRequestState:
    state = RouteRequestState(
        user_query=body.user_query,
        mode=body.mode,
        chat_history=body.chat_history,
    )
    result = handle_query(state)
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

