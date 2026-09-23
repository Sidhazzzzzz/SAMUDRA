with open('style.css', 'r', encoding='utf-8') as f:
    css = f.read()

if '.osm-dark-filter' not in css:
    css += "\n\n/* Dark Matter Filter */\n.osm-dark-filter { filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%); }\n"

with open('style.css', 'w', encoding='utf-8') as f:
    f.write(css)
