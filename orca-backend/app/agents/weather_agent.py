"""Weather agent — storm and cyclone advisory stubs."""


def get_storm_status(region_bbox: list[float]) -> dict:
    """Return mock storm/cyclone status for a bounding box [south, west, north, east]."""
    return {
        "source": "MOCK_DATA",
        "region_bbox": region_bbox,
        "active": False,
        "advisories": [],
        "wind_speed_knots": 12,
        "visibility_nm": 8,
        "forecast_window_hrs": 24,
        "summary": "No active cyclone or storm warnings in this region.",
    }
