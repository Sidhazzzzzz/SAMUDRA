"""Coastal Authority Agent - Deterministic coastal risk ranking and vessel alerts."""

from __future__ import annotations

import logging
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from shapely.geometry import Point, Polygon

from app.agents.weather_agent import get_storm_status
from app.agents.risk_agent import evaluate_verdict, calculate_hmi

logger = logging.getLogger("orca.agents.coastal_authority")

# Simulated Fleet (Part A)
# TAG: "SIMULATED_FLEET_FOR_DEMO"
SIMULATED_FLEET = [
    {"id": "V-101", "lat": 9.25, "lon": 79.15, "vessel_type": "Fishing"},
    {"id": "V-102", "lat": 9.30, "lon": 79.20, "vessel_type": "Commercial"},
    {"id": "V-103", "lat": 9.15, "lon": 79.10, "vessel_type": "Fishing"},
    {"id": "V-104", "lat": 9.40, "lon": 79.35, "vessel_type": "Fishing"},
    {"id": "V-105", "lat": 9.10, "lon": 79.60, "vessel_type": "Cargo"},
    {"id": "V-106", "lat": 9.45, "lon": 79.70, "vessel_type": "Fishing"},
    {"id": "V-107", "lat": 9.35, "lon": 79.40, "vessel_type": "Passenger"},
    {"id": "V-108", "lat": 9.20, "lon": 79.50, "vessel_type": "Fishing"},
    {"id": "V-109", "lat": 9.32, "lon": 79.55, "vessel_type": "Fishing"},
    {"id": "V-110", "lat": 9.12, "lon": 79.25, "vessel_type": "Commercial"},
    {"id": "V-111", "lat": 9.28, "lon": 79.31, "vessel_type": "Fishing"},
    {"id": "V-112", "lat": 9.27, "lon": 79.12, "vessel_type": "Fishing"},
]

def check_vessels_in_zone(polygon_coordinates: list[list[float]], fleet: list = SIMULATED_FLEET) -> list[str]:
    """Check which simulated vessel IDs fall inside the given polygon (Part B)."""
    if len(polygon_coordinates) < 3:
        return []
    
    # Shapely polygon expects (lon, lat) but we can do (lat, lon) as long as we use it consistently
    # Let's map it exactly as passed (assume polygon is [lat, lon] points)
    poly = Polygon(polygon_coordinates)
    affected_ids = []
    
    for vessel in fleet:
        pt = Point(vessel["lat"], vessel["lon"])
        if poly.contains(pt):
            affected_ids.append(vessel["id"])
            
    return affected_ids

def generate_cap_alert(event_type: str, severity: str, urgency: str, certainty: str, headline: str, description: str, polygon_coordinates: list[list[float]]) -> str:
    """Construct a valid CAP 1.2 XML document using xml.etree.ElementTree."""
    root = ET.Element("alert", xmlns="urn:oasis:names:tc:emergency:cap:1.2")
    
    ET.SubElement(root, "identifier").text = f"urn:uuid:{uuid.uuid4()}"
    ET.SubElement(root, "sender").text = "orca.coastal_authority@example.com"
    ET.SubElement(root, "sent").text = datetime.now(timezone.utc).isoformat()
    
    # NOTE: "Actual" status is used to mirror real systems for this demo scenario, 
    # but the data and broadcast are simulated.
    ET.SubElement(root, "status").text = "Actual" 
    ET.SubElement(root, "msgType").text = "Alert"
    ET.SubElement(root, "scope").text = "Public"
    
    info = ET.SubElement(root, "info")
    ET.SubElement(info, "category").text = "Met"
    ET.SubElement(info, "event").text = event_type
    ET.SubElement(info, "urgency").text = urgency
    ET.SubElement(info, "severity").text = severity
    ET.SubElement(info, "certainty").text = certainty
    ET.SubElement(info, "headline").text = headline
    ET.SubElement(info, "description").text = description
    
    area = ET.SubElement(info, "area")
    ET.SubElement(area, "areaDesc").text = "Affected Coastal Zone"
    
    # Polygon format: "lat,lon lat,lon ..." First and last points must match
    coords = [f"{pt[0]},{pt[1]}" for pt in polygon_coordinates]
    if len(coords) >= 3 and coords[0] != coords[-1]:
        coords.append(coords[0])
    
    ET.SubElement(area, "polygon").text = " ".join(coords)
    
    ET.indent(root)
    return ET.tostring(root, encoding="unicode", method="xml")

# Part C: Coastal-block risk ranking
COASTAL_BLOCKS = [
    {"name": "Rameswaram", "lat": 9.28, "lon": 79.31},
    {"name": "Mandapam", "lat": 9.27, "lon": 79.12},
    {"name": "Pamban", "lat": 9.28, "lon": 79.22},
    {"name": "Dhanushkodi", "lat": 9.19, "lon": 79.43},
    {"name": "Keelakarai", "lat": 9.23, "lon": 78.78},
]



import asyncio

async def fetch_block_data(block):
    bbox = [block["lat"] - 0.05, block["lon"] - 0.05, block["lat"] + 0.05, block["lon"] + 0.05]
    weather = await asyncio.to_thread(get_storm_status, region_bbox=bbox)
    
    verdict = evaluate_verdict(weather)
    wave = weather.get("wave_height_m")
    wind = weather.get("wind_gusts_knots")
    hmi = calculate_hmi(weather)
    
    return {
        "block_name": block["name"],
        "lat": block["lat"],
        "lon": block["lon"],
        "hmi_score": round(hmi, 2),
        "wave_height_m": wave,
        "wind_gusts_knots": wind,
        "action_tier": verdict.get("verdict"),
        "reason": verdict.get("reason"),
        "source": weather.get("source")
    }

def get_coastal_block_rankings() -> list:
    """Fetch real weather data and compute HMI for coastal blocks, returning a ranked list."""
    async def get_all():
        tasks = [fetch_block_data(block) for block in COASTAL_BLOCKS]
        return await asyncio.gather(*tasks)
    
    results = asyncio.run(get_all())
    # Sort descending by HMI score (highest risk first)
    results.sort(key=lambda x: x["hmi_score"], reverse=True)
    return results
