import re

with open('app/orchestrator.py', 'r', encoding='utf-8') as f:
    orch = f.read()

# Fix the trace summary and source_type for route computation
trace_old = r"""            elif tool_name in \["get_route_between", "plan_fishing_route", "plan_commercial_route"\]:
                waypoints = result\.get\("waypoints", \[\]\)
                summary = f"Calculated route with \{len\(waypoints\)\} waypoints, source=\{source_type\}"
"""
trace_new = """            elif tool_name in ["get_route_between", "plan_fishing_route", "plan_commercial_route"]:
                route_dict = result.get("route", {}) if tool_name == "plan_fishing_route" else result
                waypoints = route_dict.get("waypoints", [])
                err_msg = route_dict.get("error")
                
                if err_msg:
                    source_type = "error"
                    summary = f"Route error: {err_msg}"
                elif len(waypoints) == 0:
                    source_type = "error"
                    summary = "No valid route found"
                else:
                    summary = f"Calculated route with {len(waypoints)} waypoints, source={source_type}"
"""
orch = re.sub(trace_old, trace_new, orch)

# Add instruction to LLM prompt about empty routes
prompt_old = r"""    "6\. Include real SST and Chlorophyll values when present \('sea surface temperature XAC, chlorophyll Y mg/mA3 near \[location\]'\) without fabricating a value when the fetch returns null \? in that case simply omit the SST/chlorophyll line\.\\n"
    "7\. Use simple language a non-technical mariner can understand\.\\n"
\]\)"""
# Need to use standard replace since regex on those custom characters might be flaky
if "If a route was requested but the waypoints array is empty" not in orch:
    orch = orch.replace(
        '"7. Use simple language a non-technical mariner can understand.\\n"',
        '"7. If a route was requested but no waypoints were returned, explicitly state that no valid or safe route could be found.\\n"\n    "8. Use simple language a non-technical mariner can understand.\\n"'
    )

with open('app/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(orch)
