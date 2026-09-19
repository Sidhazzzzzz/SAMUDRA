"""ORCA — Maritime Decision-Support System (FastAPI entrypoint)."""

from __future__ import annotations

from fastapi import FastAPI, Response
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
