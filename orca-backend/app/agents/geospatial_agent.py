"""Geospatial agent — route computation and EEZ boundary stubs."""


def get_route_between(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    vessel_draft_m: float,
) -> dict:
    """Return a mock optimised route between two coordinates."""
    return {
        "source": "MOCK_DATA",
        "origin": {"lat": origin_lat, "lon": origin_lon},
        "destination": {"lat": dest_lat, "lon": dest_lon},
        "vessel_draft_m": vessel_draft_m,
        "distance_nm": 34.6,
        "estimated_time_hrs": 3.2,
        "waypoints": [
            {"lat": origin_lat, "lon": origin_lon, "label": "Departure"},
            {
                "lat": (origin_lat + dest_lat) / 2,
                "lon": (origin_lon + dest_lon) / 2,
                "label": "Mid-channel waypoint",
            },
            {"lat": dest_lat, "lon": dest_lon, "label": "Arrival / PFZ zone"},
        ],
    }
