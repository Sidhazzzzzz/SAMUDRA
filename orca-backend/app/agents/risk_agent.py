"""Risk assessment agent — voyage risk scoring stubs."""


def assess_voyage_risk(
    weather: dict,
    sea_conditions: dict,
    vessel_type: str,
    max_wave_tolerance_m: float,
) -> dict:
    """Return a mock risk assessment for a planned voyage."""
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
