import urllib.request, urllib.parse, json

query = """
[out:json];
(
  relation["name"~"Gulf of Mannar Biosphere Reserve", i];
  relation["name"~"Gulf of Mannar Marine National Park", i];
);
out geom;
"""

url = 'http://overpass-api.de/api/interpreter'
data = urllib.parse.urlencode({'data': query.strip()}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'})
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        result = json.loads(response.read())
        print(f'Found {len(result.get("elements", []))} elements')
        if result.get('elements'):
            for el in result['elements']:
                print(el.get('tags', {}).get('name'))
                with open('app/agents/mpa_polygons.json', 'w') as f:
                    json.dump(result, f)
except Exception as e:
    print('Failed:', e)
