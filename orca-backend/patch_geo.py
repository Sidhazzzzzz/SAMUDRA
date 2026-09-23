with open('app/agents/geospatial_agent.py', 'r') as f:
    content = f.read()

import_patch = '''from shapely.geometry import LineString, Point, shape
import os
import json
import urllib.request'''

content = content.replace('from shapely.geometry import LineString, Point', import_patch)

mpa_logic = '''
_MPA_FEATURES = []
_MPA_LOADED = False

def load_mpa_data():
    global _MPA_FEATURES, _MPA_LOADED
    if _MPA_LOADED: return
    
    url = 'https://incois.gov.in/geoserver/PFZ_Sectors/wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature&TYPENAME=PFZ_Sectors:sector_new&outputFormat=application/json'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
            _MPA_FEATURES = data.get('features', [])
    except Exception as e:
        logger.error(f"Failed to fetch MPA/Sectors: {e}")
        base_dir = os.path.dirname(__file__)
        fallback_path = os.path.join(base_dir, 'mpa_sectors.json')
        if os.path.exists(fallback_path):
            with open(fallback_path, 'r') as f:
                data = json.load(f)
                _MPA_FEATURES = data.get('features', [])
    _MPA_LOADED = True

def check_mpa_violations(waypoints: list[dict]) -> dict:
    load_mpa_data()
    if len(waypoints) < 2 or not _MPA_FEATURES:
        return {"mpa_caution": False, "mpa_name": None}
        
    route_coords = [(wp["lon"], wp["lat"]) for wp in waypoints]
    route_line = LineString(route_coords)
    
    for f in _MPA_FEATURES:
        try:
            poly = shape(f["geometry"])
            if route_line.intersects(poly):
                sector_name = f.get("properties", {}).get("SECTORNAME", "Unknown MPA")
                logger.info(f"MPA CAUTION: Route intersects MPA/Sector: {sector_name}")
                return {"mpa_caution": True, "mpa_name": sector_name}
        except Exception:
            continue
            
    return {"mpa_caution": False, "mpa_name": None}

def check_imbl_violations'''

content = content.replace('def check_imbl_violations', mpa_logic)

check_patch = '''
        imbl_check = check_imbl_violations(waypoints)
        result.update(imbl_check)
        
        mpa_check = check_mpa_violations(waypoints)
        result.update(mpa_check)

        if imbl_check["imbl_hard_violation"]:'''

content = content.replace('''
        imbl_check = check_imbl_violations(waypoints)
        result.update(imbl_check)

        if imbl_check["imbl_hard_violation"]:''', check_patch)

with open('app/agents/geospatial_agent.py', 'w') as f:
    f.write(content)
