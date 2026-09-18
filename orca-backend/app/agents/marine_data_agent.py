"""Marine data agent — provides sea-state, bathymetry stubs, and ecosystem trend analysis."""

from __future__ import annotations

from datetime import datetime, timezone


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


def analyze_ecosystem_trends(region: str, years: int = 3) -> dict:
    """Return ecosystem trend data for a coastal region over the specified period.

    Currently returns MOCK DATA — real implementation would integrate historical
    SST (Sea Surface Temperature) and chlorophyll-a concentration data from
    satellite sources such as MODIS/Aqua, Sentinel-3 OLCI, or INCOIS datasets.

    Args:
        region: Name of the coastal region (e.g. "Gulf of Mannar", "Rameswaram").
        years:  Number of years to analyse (default 3).

    Returns:
        dict with yearly data points, computed trend direction, and percentage change.
    """
    now = datetime.now(timezone.utc)
    current_year = now.year

    # Plausible mock data for the Gulf of Mannar region:
    # SST has risen slightly, chlorophyll-a has declined (consistent with
    # warming-driven stratification reducing nutrient upwelling).
    yearly_data = []
    base_sst = 28.2
    base_chl = 0.85  # mg/m³

    for i in range(years):
        yr = current_year - years + 1 + i
        sst = round(base_sst + i * 0.15, 2)        # +0.15°C per year
        chl = round(base_chl - i * 0.08, 3)         # -0.08 mg/m³ per year
        yearly_data.append({
            "year": yr,
            "mean_sst_celsius": sst,
            "mean_chlorophyll_a_mg_per_m3": chl,
        })

    # Compute trend direction from first to last data point
    first_chl = yearly_data[0]["mean_chlorophyll_a_mg_per_m3"]
    last_chl = yearly_data[-1]["mean_chlorophyll_a_mg_per_m3"]
    pct_change = round(((last_chl - first_chl) / first_chl) * 100, 1)

    if pct_change < -5:
        trend = "declining"
    elif pct_change > 5:
        trend = "improving"
    else:
        trend = "stable"

    first_sst = yearly_data[0]["mean_sst_celsius"]
    last_sst = yearly_data[-1]["mean_sst_celsius"]
    sst_pct_change = round(((last_sst - first_sst) / first_sst) * 100, 1)

    return {
        "source": "MOCK_DATA",
        "region": region,
        "analysis_period_years": years,
        "yearly_data": yearly_data,
        "trend": {
            "chlorophyll_a_direction": trend,
            "chlorophyll_a_pct_change": pct_change,
            "sst_direction": "rising" if sst_pct_change > 0 else "stable",
            "sst_pct_change": sst_pct_change,
        },
        "interpretation": (
            f"Over the past {years} years, chlorophyll-a concentration in "
            f"{region} has {trend} by {abs(pct_change)}%, while SST has "
            f"{'risen' if sst_pct_change > 0 else 'remained stable'} by "
            f"{abs(sst_pct_change)}%. Declining chlorophyll-a is associated "
            f"with reduced primary productivity and may correlate with "
            f"decreasing fish catch rates."
        ),
        "fetched_at": now.isoformat(),
    }
