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


import httpx
import os
import json
import logging

logger = logging.getLogger("orca.agents.marine_data")

from app.cache import with_cache

@with_cache(ttl=300)
def analyze_ecosystem_trends(region: str, years: int = 3) -> dict:
    """Return ecosystem trend data for a coastal region over the specified period.

    Integrates historical SST (Sea Surface Temperature) and chlorophyll-a concentration 
    data from NOAA CoastWatch ERDDAP (MODIS-Aqua monthly composites).

    Args:
        region: Name of the coastal region (e.g. "Gulf of Mannar", "Rameswaram").
        years:  Number of years to analyse (default 3).

    Returns:
        dict with yearly data points, computed trend direction, and percentage change.
    """
    now = datetime.now(timezone.utc)
    # Use max 2024 as current year to ensure dataset availability on ERDDAP
    current_year = min(now.year, 2024) 
    
    # Bounding box for Gulf of Mannar region
    lat_min, lat_max = 9.0, 9.5
    lon_min, lon_max = 79.0, 79.8
    
    yearly_data = []
    
    # 1. Fetch SST from Open-Meteo Marine API
    sst_source = "Open-Meteo Marine API"
    try:
        with httpx.Client(timeout=10.0) as client:
            for i in range(years):
                yr = current_year - years + 1 + i
                start_date = f"{yr}-12-01"
                end_date = f"{yr}-12-31"
                
                om_url = "https://marine-api.open-meteo.com/v1/marine"
                om_params = {
                    "latitude": (lat_min + lat_max) / 2.0,
                    "longitude": (lon_min + lon_max) / 2.0,
                    "start_date": start_date,
                    "end_date": end_date,
                    "hourly": "sea_surface_temperature",
                    "timezone": "UTC"
                }
                
                resp = client.get(om_url, params=om_params)
                resp.raise_for_status()
                om_data = resp.json()
                
                # Average the hourly SST for the month
                temps = [t for t in om_data.get("hourly", {}).get("sea_surface_temperature", []) if t is not None]
                mean_sst = round(sum(temps) / len(temps), 2) if temps else None
                
                yearly_data.append({
                    "year": yr,
                    "mean_sst_celsius": mean_sst,
                    "mean_chlorophyll_a_mg_per_m3": None # Placeholder, filled below
                })
    except Exception as e:
        logger.error("Open-Meteo SST fetch failed: %s", e)
        sst_source = "Unavailable (Open-Meteo unreachable)"
        # If SST fails, populate with None
        for i in range(years):
            yr = current_year - years + 1 + i
            yearly_data.append({
                "year": yr,
                "mean_sst_celsius": None,
                "mean_chlorophyll_a_mg_per_m3": None
            })

    # 2. Fetch Chlorophyll from NOAA ERDDAP
    chl_source = "Unavailable (NOAA ERDDAP unreachable)"
    endpoints = ["coastwatch.pfeg.noaa.gov", "upwell.pfeg.noaa.gov", "polarwatch.noaa.gov"]
    chl_success = False
    
    try:
        import asyncio
        async def fetch_chl_from_endpoint(endpoint):
            logger.info("Attempting ERDDAP CHL fetch via %s", endpoint)
            async with httpx.AsyncClient(timeout=15.0) as async_client:
                endpoint_yearly = []
                for i in range(years):
                    yr = yearly_data[i]["year"]
                    time_str = f"{yr}-01-16T12:00:00Z"
                    chl_url = f"https://{endpoint}/erddap/griddap/erdMH1chlamday.json?chlorophyll[({time_str}):1:({time_str})][({lat_min}):1:({lat_max})][({lon_min}):1:({lon_max})]"
                    chl_resp = await async_client.get(chl_url)
                    chl_resp.raise_for_status()
                    chl_rows = chl_resp.json().get("table", {}).get("rows", [])
                    valid_chl = [r[-1] for r in chl_rows if r[-1] is not None]
                    mean_chl = round(sum(valid_chl) / len(valid_chl), 3) if valid_chl else None
                    endpoint_yearly.append(mean_chl)
                return endpoint, endpoint_yearly

        async def fetch_any_chl():
            tasks = [asyncio.create_task(fetch_chl_from_endpoint(ep)) for ep in endpoints]
            pending = tasks
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    try:
                        res_endpoint, res_yearly = task.result()
                        for t in pending:
                            t.cancel()
                        return res_endpoint, res_yearly
                    except Exception as e:
                        logger.warning("Endpoint failed for CHL: %s", e)
            raise Exception("All ERDDAP endpoints failed")

        from concurrent.futures import ThreadPoolExecutor
        def _run_async():
            return asyncio.run(fetch_any_chl())
        with ThreadPoolExecutor(1) as pool:
            success_ep, success_yearly = pool.submit(_run_async).result()
        for i in range(years):
            yearly_data[i]["mean_chlorophyll_a_mg_per_m3"] = success_yearly[i]
        chl_source = f"NOAA ERDDAP via {success_ep} (erdMH1chlamday)"
        chl_success = True
            
    except Exception as exc:
        logger.error("ERDDAP API multi-endpoint CHL fetch failed: %s", exc)
        # Attempt fallback for Chl if it fails
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            fallback_path = os.path.join(base_dir, 'data', 'fallback', 'ecosystem_fallback_snapshot.json')
            if os.path.exists(fallback_path):
                with open(fallback_path, 'r') as f:
                    fb = json.load(f)
                now_str = now.strftime('%Y-%m-%d')
                chl_source = f"LOCAL_FALLBACK_SNAPSHOT (live ERDDAP failed on {now_str}, returning last genuine fetch)"
                # Merge fallback CHL into yearly_data
                for i, fb_yd in enumerate(fb.get("yearly_data", [])):
                    if i < len(yearly_data):
                        yearly_data[i]["mean_chlorophyll_a_mg_per_m3"] = fb_yd.get("mean_chlorophyll_a_mg_per_m3")
        except Exception as fallback_e:
            logger.error("Ecosystem fallback snapshot failed to load for CHL: %s", fallback_e)

    # Compute trend direction from first to last data point (handling Nones safely)
    trend_dict = {}
    
    # CHL Trend
    first_chl = yearly_data[0].get("mean_chlorophyll_a_mg_per_m3")
    last_chl = yearly_data[-1].get("mean_chlorophyll_a_mg_per_m3")
    if first_chl is not None and last_chl is not None and first_chl != 0:
        pct_change = round(((last_chl - first_chl) / first_chl) * 100, 1)
        if pct_change < -5:
            trend_dict["chlorophyll_a_direction"] = "declining"
        elif pct_change > 5:
            trend_dict["chlorophyll_a_direction"] = "improving"
        else:
            trend_dict["chlorophyll_a_direction"] = "stable"
        trend_dict["chlorophyll_a_pct_change"] = pct_change
    else:
        trend_dict["chlorophyll_a_direction"] = "unavailable"
        trend_dict["chlorophyll_a_pct_change"] = None

    # SST Trend
    first_sst = yearly_data[0].get("mean_sst_celsius")
    last_sst = yearly_data[-1].get("mean_sst_celsius")
    if first_sst is not None and last_sst is not None and first_sst != 0:
        sst_pct_change = round(((last_sst - first_sst) / first_sst) * 100, 1)
        trend_dict["sst_direction"] = "rising" if sst_pct_change > 0 else "stable"
        trend_dict["sst_pct_change"] = sst_pct_change
    else:
        trend_dict["sst_direction"] = "unavailable"
        trend_dict["sst_pct_change"] = None

    result = {
        "source": {
            "sst": sst_source,
            "chlorophyll": chl_source
        },
        "region": region,
        "analysis_period_years": years,
        "yearly_data": yearly_data,
        "trend": trend_dict,
        "interpretation": "Refer to explicit trend values in generated LLM narration.",
        "fetched_at": now.isoformat(),
    }

    # Save to fallback snapshot if ERDDAP was successful (to preserve a genuine snapshot)
    if chl_success:
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            fallback_dir = os.path.join(base_dir, 'data', 'fallback')
            os.makedirs(fallback_dir, exist_ok=True)
            fallback_path = os.path.join(fallback_dir, 'ecosystem_fallback_snapshot.json')
            with open(fallback_path, 'w') as f:
                json.dump(result, f, indent=4)
        except Exception as e:
            logger.error("Failed to save ecosystem snapshot: %s", e)

    return result

