"""Marine data agent — provides sea-state and bathymetry stubs."""


def get_sea_conditions(region_bbox: list[float]) -> dict:
    """Return mock sea-state data for a bounding box [south, west, north, east]."""
    return {
        "source": "MOCK_DATA",
        "region_bbox": region_bbox,
        "sea_state": {
            "significant_wave_height_m": 1.2,
            "swell_direction_deg": 210,
            "sea_surface_temp_c": 28.4,
            "current_speed_knots": 0.8,
            "current_direction_deg": 185,
        },
        "bathymetry": {
            "avg_depth_m": 42,
            "min_depth_m": 12,
            "max_depth_m": 78,
        },
    }
