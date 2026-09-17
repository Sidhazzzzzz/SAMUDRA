"""Reporting agent — human-readable advisory generation stubs."""


def generate_advisory(state_snapshot: dict) -> dict:
    """Return a mock plain-text advisory summary from the current state."""
    return {
        "source": "MOCK_DATA",
        "advisory_text": (
            "ORCA Advisory (MOCK): Based on current data, sea conditions are "
            "favourable near Rameswaram. 3 Potential Fishing Zones have been "
            "identified. No active storm warnings. Risk level: LOW. "
            "Recommended departure window: next 6 hours."
        ),
        "language": "en",
    }
