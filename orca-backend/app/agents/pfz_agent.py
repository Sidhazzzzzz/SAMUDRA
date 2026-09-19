import urllib.request
import json
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(dlon))
    initial_bearing = math.atan2(x, y)
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360
    return round(compass_bearing)

def get_nearest_landing_centre(origin_lat: float, origin_lon: float) -> tuple[dict | None, str | None]:
    url_lc = "https://incois.gov.in/geoserver/PFZ_LandingCentres/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_LandingCentres:LandingCenters_29Apr2024&outputFormat=application/json"
    nearest_lc = None
    min_dist = float('inf')
    updated_date = None
    try:
        req = urllib.request.Request(url_lc, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            lc_data = json.loads(response.read().decode('utf-8'))
            for f in lc_data.get('features', []):
                p = f.get('properties', {})
                lc_lat = p.get('LATITUDE')
                lc_lon = p.get('LONGITUDE')
                if lc_lat is not None and lc_lon is not None:
                    dist = haversine(origin_lat, origin_lon, float(lc_lat), float(lc_lon))
                    if dist < min_dist:
                        min_dist = dist
                        nearest_lc = p
    except Exception as e:
        print(f"Error fetching Landing Centres: {e}")

    lc_info = None
    if nearest_lc:
        lc_lat = float(nearest_lc['LATITUDE'])
        lc_lon = float(nearest_lc['LONGITUDE'])
        actual_bearing = calculate_bearing(origin_lat, origin_lon, lc_lat, lc_lon)
        
        lc_info = {
            "LC_NAME": nearest_lc.get("LC_NAME"),
            "DIRECTION": nearest_lc.get("DIRECTION"),
            "BEARING": actual_bearing,
            "DISTANCE_F": round(min_dist, 1),
            "DISTANCE_T": nearest_lc.get("DISTANCE_T"),
            "DEPTH_FROM": nearest_lc.get("DEPTH_FROM"),
            "DEPTH_TO": nearest_lc.get("DEPTH_TO")
        }
        updated_date = nearest_lc.get("UPDATED_DA")
    
    return lc_info, updated_date

def get_active_pfz(region_bbox: list[float], origin_lat: float = 9.2885, origin_lon: float = 79.3129) -> dict:
    """Return real PFZ advisories for a bounding box [south, west, north, east]."""
    south, west, north, east = region_bbox
    bbox_str = f"{west},{south},{east},{north},EPSG:4326"
    
    # 1. Fetch PFZ lines
    url_pfz = f"https://incois.gov.in/geoserver/PFZ_Automation/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_Automation:pfzlines&outputFormat=application/json&BBOX={bbox_str}"
    
    pfz_features = []
    fetch_failed = False
    try:
        req = urllib.request.Request(url_pfz, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
            pfz_features = data.get('features', [])
    except Exception as e:
        print(f"Error fetching PFZ lines: {e}")
        fetch_failed = True

    if fetch_failed:
        import os
        from datetime import datetime
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            fallback_path = os.path.join(base_dir, 'data', 'fallback', 'pfz_fallback_snapshot.json')
            with open(fallback_path, 'r') as f:
                fb = json.load(f)
            fb['source'] = f"LOCAL_FALLBACK_SNAPSHOT (captured 2026-09-19, live fetch failed)"
            return fb
        except Exception as fallback_e:
            return {"source": "LOCAL_FALLBACK_SNAPSHOT", "error": str(fallback_e)}

    if not pfz_features:
        return {
            "source": "INCOIS GeoServer",
            "message": "no active PFZ advisory for this sector today",
            "pfz_count": 0,
            "pfz_lines": []
        }

    # Extract PFZ metadata
    first_pfz = pfz_features[0]
    props = first_pfz.get('properties', {})
    sector = props.get('State_Name', 'Unknown')
    year = props.get('Year')
    jday = props.get('Julian_day')
    
    # 2. Fetch nearest Landing Centre
    lc_info, updated_date = get_nearest_landing_centre(origin_lat, origin_lon)

    # 3. Fetch SST and CHL
    s_bbox = f"{origin_lon-0.05},{origin_lat-0.05},{origin_lon+0.05},{origin_lat+0.05}"
    
    sst_val = None
    try:
        url_sst = f"https://incois.gov.in/geoserver/PFZ-TUNA-SST-CHL/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo&LAYERS=PFZ-TUNA-SST-CHL:sst&QUERY_LAYERS=PFZ-TUNA-SST-CHL:sst&INFO_FORMAT=application/json&FEATURE_COUNT=1&X=1&Y=1&WIDTH=3&HEIGHT=3&BBOX={s_bbox}&SRS=EPSG:4326"
        req = urllib.request.Request(url_sst, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            d = json.loads(response.read().decode('utf-8'))
            f = d.get('features', [])
            if f:
                sst_val = f[0].get('properties', {}).get('GRAY_INDEX')
    except Exception as e:
        print(f"Error fetching SST: {e}")

    chl_val = None
    try:
        url_chl = f"https://incois.gov.in/geoserver/PFZ-TUNA-SST-CHL/wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo&LAYERS=PFZ-TUNA-SST-CHL:chl&QUERY_LAYERS=PFZ-TUNA-SST-CHL:chl&INFO_FORMAT=application/json&FEATURE_COUNT=1&X=1&Y=1&WIDTH=3&HEIGHT=3&BBOX={s_bbox}&SRS=EPSG:4326"
        req = urllib.request.Request(url_chl, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            d = json.loads(response.read().decode('utf-8'))
            f = d.get('features', [])
            if f:
                chl_val = f[0].get('properties', {}).get('GRAY_INDEX')
    except Exception as e:
        print(f"Error fetching CHL: {e}")

    return {
        "source": "INCOIS GeoServer (PFZ_Automation, PFZ_LandingCentres)",
        "advisory_date": updated_date or f"{year} Julian Day {jday}",
        "region_bbox": region_bbox,
        "sector": sector,
        "pfz_count": len(pfz_features),
        "pfz_lines": pfz_features,
        "nearest_landing_centre": lc_info,
        "sst_celsius": sst_val,
        "chlorophyll_mgm3": chl_val
    }
