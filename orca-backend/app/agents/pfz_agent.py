"""PFZ (Potential Fishing Zone) agent — INCOIS PFZ advisory stubs."""


def get_active_pfz(region_bbox: list[float]) -> dict:
    """Return mock PFZ advisories for a bounding box [south, west, north, east].

    Centroids are placed near Rameswaram, Tamil Nadu.
    """
    return {
        "source": "MOCK_DATA",
        "region_bbox": region_bbox,
        "pfz_count": 3,
        "pfz_zones": [
            {
                "id": "PFZ-TN-001",
                "centroid_lat": 9.35,
                "centroid_lon": 79.45,
                "radius_nm": 5,
                "species_likely": ["Tuna", "Mackerel"],
                "confidence": 0.87,
                "valid_from": "2026-09-17T00:00:00Z",
                "valid_until": "2026-09-18T00:00:00Z",
                "source": "MOCK_DATA",
            },
            {
                "id": "PFZ-TN-002",
                "centroid_lat": 9.22,
                "centroid_lon": 79.60,
                "radius_nm": 4,
                "species_likely": ["Sardine", "Anchovy"],
                "confidence": 0.75,
                "valid_from": "2026-09-17T00:00:00Z",
                "valid_until": "2026-09-18T00:00:00Z",
                "source": "MOCK_DATA",
            },
            {
                "id": "PFZ-TN-003",
                "centroid_lat": 9.40,
                "centroid_lon": 79.30,
                "radius_nm": 6,
                "species_likely": ["Seer Fish"],
                "confidence": 0.68,
                "valid_from": "2026-09-17T00:00:00Z",
                "valid_until": "2026-09-18T00:00:00Z",
                "source": "MOCK_DATA",
            },
        ],
    }
