import re

with open('app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

# Replace PFZ color (06D6A0) to Safe Depth Blue (5C8CA3)
app_js = app_js.replace('#06D6A0', '#5C8CA3')

# Replace Route Color (FFD166) to Chart Black (111111)
app_js = app_js.replace("color: '#FFD166'", "color: '#111111'")

# Replace Destination Marker Color (EF476F) to Chart Black or Dark Gray
app_js = app_js.replace("color: '#EF476F'", "color: '#111111'")

# Replace weather blob caution (FFD166) with actual hazard yellow (FFD700)
app_js = app_js.replace("blobColor = '#FFD166';", "blobColor = '#FFD700';")

# Replace weather blob danger (EF476F) with chart magenta (D81B60)
app_js = app_js.replace("blobColor = '#EF476F';", "blobColor = '#D81B60';")

# Also replace hardcoded tooltip fill colors (#1C2541) with buff (#F4EFEA)
app_js = app_js.replace("fillColor: '#1C2541'", "fillColor: '#F4EFEA'")

with open('app.js', 'w', encoding='utf-8') as f:
    f.write(app_js)
