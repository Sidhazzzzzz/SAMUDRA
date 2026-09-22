"""Risk assessment agent — deterministic verdict evaluation and voyage risk scoring."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("orca.agents.risk")

# Threshold constants matching weather_agent
WAVE_HEIGHT_MAX_M = 2.5
WIND_GUSTS_MAX_KNOTS = 25.0

# Caution margins (within 20% of maximum thresholds)
WAVE_HEIGHT_CAUTION_M = 2.0     # 2.5 * 0.80
WIND_GUSTS_CAUTION_KNOTS = 20.0  # 25.0 * 0.80


def evaluate_verdict(
    weather_result: dict,
    pfz_result: dict | None = None,
    route_result: dict | None = None,
) -> dict:
    """Pure Python deterministic risk/verdict evaluator.

    Takes already-fetched data and computes an operational verdict using ONLY
    code logic — no LLM call is made inside this function.

    Priority order:
      1. weather_result["data_unavailable"] is True
         -> CAUTION ("Live weather data unavailable — proceed with local knowledge and visual checks.")
      2. weather_result["active"] is True
         -> NO-GO (reason from specific advisory warnings)
      3. wave_height_m >= 2.0m (within 20% of 2.5m) OR wind_gusts_knots >= 20.0 (within 20% of 25.0)
         -> CAUTION ("Conditions approaching operational limits: [exact values].")
      4. Else
         -> SAFE ("Conditions within normal operational limits.")

    Returns:
      {"verdict": "SAFE" | "CAUTION" | "NO-GO", "reason": str, "evaluated_at": ISO timestamp}
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    result = None

    # Priority 1: Data unavailable
    if not weather_result or weather_result.get("data_unavailable") is True:
        result = {
            "verdict": "CAUTION",
            "reason": "Live weather data unavailable — proceed with local knowledge and visual checks.",
            "evaluated_at": now_iso,
        }

    is_fallback = False
    if not result:
        weather_src = weather_result.get("source", "") if weather_result else ""
        pfz_src = pfz_result.get("source", "") if pfz_result else ""
        if "LOCAL_FALLBACK_SNAPSHOT" in weather_src or "LOCAL_FALLBACK_SNAPSHOT" in pfz_src:
            is_fallback = True

        # Priority 2: Active storm / severe condition triggered
        if weather_result.get("active") is True:
            advisories = weather_result.get("advisories", [])
            if advisories:
                reason = " ".join(advisories)
            else:
                reason = weather_result.get(
                    "summary", "Active hazardous marine weather conditions detected."
                )

            if is_fallback:
                reason += " (NOTE: Live data unreachable; using last known fallback snapshot. Treat with extra caution.)"

            result = {
                "verdict": "NO-GO",
                "reason": reason,
                "evaluated_at": now_iso,
                "fallback_used": is_fallback,
            }

    if not result:
        # Priority 2.5: Lightning risk
        lightning_risk = weather_result.get("lightning_risk", 0.0)
        LIGHTNING_THRESHOLD = 0.7

        if lightning_risk >= LIGHTNING_THRESHOLD:
            reason = (
                f"Elevated lightning risk ({lightning_risk:.0%}) in the operational area. "
                "Avoid open-deck operations and seek shelter if thunderstorm develops."
            )
            if is_fallback:
                reason += " (NOTE: Live data unreachable; using last known fallback snapshot.)"
            result = {
                "verdict": "CAUTION",
                "reason": reason,
                "evaluated_at": now_iso,
                "fallback_used": is_fallback,
            }

    if not result:
        # Priority 3: Within 20% of threshold limits
        wave_height = weather_result.get("wave_height_m")
        wind_gusts = weather_result.get("wind_gusts_knots")

        near_wave_limit = wave_height is not None and wave_height >= WAVE_HEIGHT_CAUTION_M
        near_wind_limit = wind_gusts is not None and wind_gusts >= WIND_GUSTS_CAUTION_KNOTS

        if near_wave_limit or near_wind_limit:
            details: list[str] = []
            if near_wave_limit:
                details.append(f"wave height {wave_height:.2f}m (limit {WAVE_HEIGHT_MAX_M}m)")
            if near_wind_limit:
                details.append(f"wind gusts {wind_gusts:.1f} knots (limit {WIND_GUSTS_MAX_KNOTS} knots)")

            reason = f"Conditions approaching operational limits: {', '.join(details)}."
            if is_fallback:
                reason += " (NOTE: Live data unreachable; using last known fallback snapshot.)"
            result = {
                "verdict": "CAUTION",
                "reason": reason,
                "evaluated_at": now_iso,
                "fallback_used": is_fallback,
            }

    if not result:
        # Priority 4: Safe
        reason = "Conditions within normal operational limits."
        if is_fallback:
            reason += " (NOTE: Live data unreachable; using last known fallback snapshot. Validate locally.)"

        result = {
            "verdict": "SAFE",
            "reason": reason,
            "evaluated_at": now_iso,
            "fallback_used": is_fallback,
        }

    # If forecast, prepend forecast label
    if weather_result and weather_result.get("is_forecast"):
        target = weather_result.get("target_time", "requested time")
        result["reason"] = f"Forecast for {target}: " + result["reason"]

    return result


def assess_voyage_risk(
    weather: dict,
    sea_conditions: dict,
    vessel_type: str,
    max_wave_tolerance_m: float,
) -> dict:
    """Return a mock risk assessment for a planned voyage (legacy stub)."""
    return {
        "source": "MOCK_DATA",
        "overall_risk_level": "LOW",
        "risk_score": 0.15,
        "factors": [
            {"factor": "Wave height vs. vessel tolerance", "status": "OK"},
            {"factor": "Storm advisories", "status": "CLEAR"},
            {"factor": "Visibility", "status": "GOOD"},
        ],
        "recommendation": "Conditions are favourable for departure.",
    }
