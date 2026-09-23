import urllib.request, urllib.parse, json

query = """
[out:json];
relation["name"~"Gulf of Mannar Marine National Park", i];
out body;
>;
out skel qt;
"""

url = 'http://overpass-api.de/api/interpreter'
data = urllib.parse.urlencode({'data': query.strip()}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'})
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        result = json.loads(response.read())
        print(f'Found {len(result.get("elements", []))} elements')
        if result.get('elements'):
            with open('app/agents/osm_mpa.json', 'w') as f:
                json.dump(result, f)
except Exception as e:
    print('Failed:', e)
