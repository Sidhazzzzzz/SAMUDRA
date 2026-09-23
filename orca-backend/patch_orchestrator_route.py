with open('app/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Update get_route_between
old_1 = '''        elif tool_name == "get_route_between":
            state.optimized_route = result.get("waypoints", [])'''
new_1 = '''        elif tool_name == "get_route_between":
            state.optimized_route = result.get("waypoints", [])
            state.route_details = result'''
content = content.replace(old_1, new_1)

# Update plan_fishing_route
old_2 = '''            if result.get("storm") is not None:
                state.weather_risks = [result["storm"]]
            state.optimized_route = result.get("route", {}).get("waypoints", [])'''
new_2 = '''            if result.get("storm") is not None:
                state.weather_risks = [result["storm"]]
            state.optimized_route = result.get("route", {}).get("waypoints", [])
            state.route_details = result.get("route", {})'''
content = content.replace(old_2, new_2)

# Update plan_commercial_route
old_3 = '''        elif tool_name == "plan_commercial_route":
            state.optimized_route = result.get("waypoints", [])'''
new_3 = '''        elif tool_name == "plan_commercial_route":
            state.optimized_route = result.get("waypoints", [])
            state.route_details = result'''
content = content.replace(old_3, new_3)

# Update evaluate_verdict call
old_4 = '''    route_data = {"waypoints": state.optimized_route} if state.optimized_route else None'''
new_4 = '''    route_data = state.route_details'''
content = content.replace(old_4, new_4)

with open('app/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)
