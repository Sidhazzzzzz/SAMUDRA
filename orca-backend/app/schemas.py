"""Pydantic models for the ORCA maritime decision-support system."""

from __future__ import annotations

from pydantic import BaseModel


class VesselTelemetry(BaseModel):
    lat: float
    lon: float
    vessel_type: str
    max_wave_tolerance_m: float
    current_fuel_liters: float
    fuel_burn_rate_lph: float
    speed_knots: float


class RouteRequestState(BaseModel):
    user_query: str
    mode: str = "fishing"
    detected_language: str = "en"
    chat_history: list[dict] = []
    vessel: VesselTelemetry | None = None
    bounding_box: tuple[float, float, float, float] | None = None
    pfz_targets: list[dict] = []
    weather_risks: list[dict] = []
    optimized_route: list[dict] = []
    route_details: dict = {}
    execution_trace: list[dict] = []
    verdict: dict | None = None
    status: str | None = None
    legal_status: bool | None = None
    abort_reason: str | None = None
    final_advisory_text: str | None = None
