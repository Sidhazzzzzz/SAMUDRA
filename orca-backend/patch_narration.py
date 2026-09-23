with open('app/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

mpa_narration = "or geospatial data not present in the input. Explicitly forbidden: mentioning fish species or confidence percentages (this data does not exist in the real source).\\n\"\\\n    \"4. If mpa_caution is true, clearly mention the route intersects the provided MPA/Sector name, using only the provided name without inventing regulatory language.\\n\""

content = content.replace('or geospatial data not present in the input. Explicitly forbidden: mentioning fish species or confidence percentages (this data does not exist in the real source).\\n"', mpa_narration)

# Also fix the rule numbers that shifted
content = content.replace('"4. When describing', '"5. When describing')
content = content.replace('"5. Include real SST', '"6. Include real SST')
content = content.replace('"6. Use simple', '"7. Use simple')
content = content.replace('"7. Keep the response', '"8. Keep the response')


with open('app/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)
