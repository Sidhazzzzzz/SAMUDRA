"""Weather agent — live marine weather and storm risk assessment via Open-Meteo."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
import httpx

logger = logging.getLogger("orca.agents.weather")

OPEN_METEO_MARINE_URL = os.getenv(
    "OPEN_METEO_MARINE_URL", "https://marine-api.open-meteo.com/v1/marine"
)
OPEN_METEO_WEATHER_URL = os.getenv(
    "OPEN_METEO_WEATHER_URL", "https://api.open-meteo.com/v1/forecast"
)

# Thresholds for elevated marine risk
WAVE_HEIGHT_THRESHOLD_M = 2.5
WIND_GUST_THRESHOLD_KNOTS = 25.0
WIND_SPEED_THRESHOLD_KNOTS = 20.0
REQUEST_TIMEOUT_SECONDS = 8.0


from app.cache import with_cache

class _HiddenArg:
    def __init__(self, val):
        self.val = val
    def __str__(self):
        return "hidden"

def get_storm_status(region_bbox: list[float] | None = None, target_time: str = "now") -> dict:
    """Fetch live marine wave and wind conditions from Open-Meteo Marine API.

    Evaluates whether conditions exceed safe operating thresholds for fishing
    vessels in the given bounding box [south, west, north, east].
    """
    if region_bbox and len(region_bbox) == 4:
        lat_full = (region_bbox[0] + region_bbox[2]) / 2.0
        lon_full = (region_bbox[1] + region_bbox[3]) / 2.0
    else:
        lat_full = 9.25
        lon_full = 79.4
        region_bbox = [9.0, 79.0, 9.5, 79.8]

    # Coarsen specifically for cache key
    lat_key = round(lat_full, 2)
    lon_key = round(lon_full, 2)

    return _fetch_storm_status_cached(
        lat_key, 
        lon_key, 
        target_time, 
        _HiddenArg(round(lat_full, 4)), 
        _HiddenArg(round(lon_full, 4)), 
        _HiddenArg(region_bbox)
    )

@with_cache(ttl=300)
def _fetch_storm_status_cached(lat_key: float, lon_key: float, target_time: str, exact_lat: _HiddenArg, exact_lon: _HiddenArg, exact_bbox: _HiddenArg) -> dict:
    lat = exact_lat.val
    lon = exact_lon.val
    region_bbox = exact_bbox.val

    now_iso = datetime.now(timezone.utc).isoformat()
    source_label = f"Open-Meteo Marine API ({now_iso})"

    is_forecast = False
    
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            target = target_time.lower().strip()
            if target == "now" or target == "today":
                # Current conditions
                marine_resp = client.get(
                    OPEN_METEO_MARINE_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": ["wave_height", "wind_wave_height", "swell_wave_height"],
                    },
                )
                marine_resp.raise_for_status()
                marine_curr = marine_resp.json().get("current", {})

                weather_resp = client.get(
                    OPEN_METEO_WEATHER_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": ["wind_speed_10m", "wind_gusts_10m"],
                        "wind_speed_unit": "kn",
                    },
                )
                weather_resp.raise_for_status()
                weather_curr = weather_resp.json().get("current", {})

                wave_height = marine_curr.get("wave_height")
                wind_wave_height = marine_curr.get("wind_wave_height")
                swell_wave_height = marine_curr.get("swell_wave_height")
                wind_speed_knots = weather_curr.get("wind_speed_10m")
                wind_gusts_knots = weather_curr.get("wind_gusts_10m")
            else:
                # Forecast logic
                is_forecast = True
                source_label = f"Open-Meteo API (Forecast for {target_time})"
                
                # Fetch hourly data
                marine_resp = client.get(
                    OPEN_METEO_MARINE_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "hourly": ["wave_height", "wind_wave_height", "swell_wave_height"],
                        "timezone": "Asia/Kolkata",
                        "forecast_days": 3
                    },
                )
                marine_resp.raise_for_status()
                marine_hourly = marine_resp.json().get("hourly", {})
                
                weather_resp = client.get(
                    OPEN_METEO_WEATHER_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "hourly": ["wind_speed_10m", "wind_gusts_10m"],
                        "wind_speed_unit": "kn",
                        "timezone": "Asia/Kolkata",
                        "forecast_days": 3
                    },
                )
                weather_resp.raise_for_status()
                weather_hourly = weather_resp.json().get("hourly", {})
                
                # Resolve index
                times = marine_hourly.get("time", [])
                
                target_hour = 12
                if "morning" in target: target_hour = 8
                elif "evening" in target or "night" in target: target_hour = 18
                
                today_date = times[0][:10]
                today_dt = datetime.strptime(today_date, "%Y-%m-%d")
                
                if "tomorrow" in target:
                    from datetime import timedelta
                    target_dt = today_dt + timedelta(days=1)
                else:
                    target_dt = today_dt
                
                target_str = f"{target_dt.strftime('%Y-%m-%d')}T{target_hour:02d}:00"
                
                try:
                    idx = times.index(target_str)
                except ValueError:
                    idx = target_hour + (24 if "tomorrow" in target else 0)
                    idx = min(idx, len(times)-1)
                    
                wave_height = marine_hourly.get("wave_height", [])[idx]
                wind_wave_height = marine_hourly.get("wind_wave_height", [])[idx]
                swell_wave_height = marine_hourly.get("swell_wave_height", [])[idx]
                wind_speed_knots = weather_hourly.get("wind_speed_10m", [])[idx]
                wind_gusts_knots = weather_hourly.get("wind_gusts_10m", [])[idx]

        # Allow test overrides if specified in environment
        if os.getenv("ORCA_FORCE_WAVE_HEIGHT"):
            wave_height = float(os.environ["ORCA_FORCE_WAVE_HEIGHT"])
        if os.getenv("ORCA_FORCE_WIND_GUSTS"):
            wind_gusts_knots = float(os.environ["ORCA_FORCE_WIND_GUSTS"])

        # Evaluate risk against thresholds
        advisories: list[str] = []
        is_elevated_risk = False

        if wave_height is not None and wave_height > WAVE_HEIGHT_THRESHOLD_M:
            is_elevated_risk = True
            advisories.append(
                f"High wave warning: Significant wave height is {wave_height:.2f}m "
                f"(exceeds safety threshold of {WAVE_HEIGHT_THRESHOLD_M}m)."
            )

        if wind_gusts_knots is not None and wind_gusts_knots > WIND_GUST_THRESHOLD_KNOTS:
            is_elevated_risk = True
            advisories.append(
                f"Severe wind gust warning: Gusts reaching {wind_gusts_knots:.1f} knots "
                f"(exceeds safety threshold of {WIND_GUST_THRESHOLD_KNOTS} knots)."
            )
        elif wind_speed_knots is not None and wind_speed_knots > WIND_SPEED_THRESHOLD_KNOTS:
            is_elevated_risk = True
            advisories.append(
                f"Strong wind warning: Sustained wind speed reaching {wind_speed_knots:.1f} knots "
                f"(exceeds safety threshold of {WIND_SPEED_THRESHOLD_KNOTS} knots)."
            )

        if is_elevated_risk:
            summary = (
                f"Elevated marine risk detected near ({lat}, {lon}): "
                f"waves {wave_height}m, wind gusts {wind_gusts_knots} knots. Caution advised."
            )
        else:
            summary = (
                f"No active storm warnings near ({lat}, {lon}): "
                f"wave height {wave_height}m, wind speed {wind_speed_knots} knots "
                f"(gusts {wind_gusts_knots} knots). Conditions within normal limits."
            )

        result = {
            "source": source_label,
            "fetched_at": now_iso,
            "is_forecast": is_forecast,
            "target_time": target_time,
            "region_bbox": region_bbox,
            "evaluated_point": {"latitude": lat, "longitude": lon},
            "active": is_elevated_risk,
            "data_unavailable": False,
            "wave_height_m": wave_height,
            "wind_wave_height_m": wind_wave_height,
            "swell_wave_height_m": swell_wave_height,
            "wind_speed_knots": wind_speed_knots,
            "wind_gusts_knots": wind_gusts_knots,
            "advisories": advisories,
            "forecast_window_hrs": 24,
            "summary": summary,
        }

        # Save successful fetch as fallback snapshot (mirrors marine_data_agent.py)
        try:
            import json as _json
            base_dir = os.path.dirname(os.path.dirname(__file__))
            fallback_dir = os.path.join(base_dir, 'data', 'fallback')
            os.makedirs(fallback_dir, exist_ok=True)
            fallback_path = os.path.join(fallback_dir, 'weather_fallback_snapshot.json')
            snapshot = dict(result)
            snapshot['captured_at'] = datetime.now(timezone.utc).isoformat()
            with open(fallback_path, 'w') as f:
                _json.dump(snapshot, f, indent=4)
        except Exception as snap_e:
            logger.error("Failed to save weather snapshot: %s", snap_e)

        return result

    except Exception as exc:
        logger.error("Open-Meteo Marine API fetch failed: %s", exc)
        
        try:
            import json
            base_dir = os.path.dirname(os.path.dirname(__file__))
            fallback_path = os.path.join(base_dir, 'data', 'fallback', 'weather_fallback_snapshot.json')
            with open(fallback_path, 'r') as f:
                fb = json.load(f)
            fb['source'] = f"LOCAL_FALLBACK_SNAPSHOT (captured {fb.get('captured_at', 'unknown date')}, live fetch failed)"
            return fb
        except Exception as fallback_e:
            logger.error(f"Fallback snapshot failed to load: {fallback_e}")
            return {
                "source": source_label,
                "fetched_at": now_iso,
                "region_bbox": region_bbox,
                "evaluated_point": {"latitude": lat, "longitude": lon},
                "active": None,
                "data_unavailable": True,
                "reason": f"Failed to retrieve marine weather from Open-Meteo: {type(exc).__name__} - {str(exc)}",
                "wave_height_m": None,
                "wind_speed_knots": None,
                "wind_gusts_knots": None,
                "advisories": ["Live marine weather data is currently unavailable."],
                "forecast_window_hrs": 24,
                "summary": "Live marine weather data is currently unavailable due to an API or network issue.",
            }
