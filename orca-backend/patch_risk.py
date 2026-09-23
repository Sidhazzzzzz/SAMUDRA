with open('app/agents/risk_agent.py', 'r') as f:
    content = f.read()

mpa_patch = '''
    if not result:
        # Priority 2.75: MPA Caution
        if route_result and route_result.get("mpa_caution"):
            mpa_name = route_result.get("mpa_name", "Protected Area")
            reason = (
                f"Route intersects Marine Protected Area (MPA) / Sector: {mpa_name}. "
                "Ensure compliance with local regulations."
            )
            if is_fallback:
                reason += " (NOTE: Live data unreachable; using last known fallback snapshot.)"
            result = {
                "verdict": "CAUTION",
                "reason": reason,
                "evaluated_at": now_iso,
                "fallback_used": is_fallback,
            }

    if not result:
        # Priority 3: Within 20% of threshold limits'''

content = content.replace('''
    if not result:
        # Priority 3: Within 20% of threshold limits''', mpa_patch)

with open('app/agents/risk_agent.py', 'w') as f:
    f.write(content)
