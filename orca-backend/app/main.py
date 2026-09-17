"""ORCA — Maritime Decision-Support System (FastAPI entrypoint)."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from app.schemas import RouteRequestState
from app.orchestrator import handle_query

app = FastAPI(
    title="ORCA — Maritime Decision-Support System",
    version="0.1.0",
    description="Agentic backend for fishing-route planning, PFZ lookup, and storm advisories.",
)


# ── Request body for /query ────────────────────────────────────────────────
class QueryRequest(BaseModel):
    user_query: str


# ── Endpoints ──────────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/query")
async def query(body: QueryRequest) -> RouteRequestState:
    state = RouteRequestState(user_query=body.user_query)
    result = handle_query(state)
    return result
