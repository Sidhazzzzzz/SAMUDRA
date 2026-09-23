import json
with open('app/agents/mpa_sectors.json') as f:
    data = json.load(f)
for f in data.get('features', []):
    coords = f['geometry']['coordinates'][0][0]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    print(f"{f['properties'].get('SECTORNAME')}: Lon [{min(lons):.2f}, {max(lons):.2f}], Lat [{min(lats):.2f}, {max(lats):.2f}]")
