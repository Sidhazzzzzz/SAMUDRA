"""ORCA — Maritime Decision-Support System (FastAPI entrypoint)."""

from __future__ import annotations

from fastapi import FastAPI, Response, Query
from fastapi.middleware.cors import CORSMiddleware
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


# ── Endpoints ──────────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/query")
async def query(body: QueryRequest) -> RouteRequestState:
    state = RouteRequestState(user_query=body.user_query, mode=body.mode)
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

