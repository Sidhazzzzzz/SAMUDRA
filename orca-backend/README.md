# ORCA — Maritime Decision-Support System

A mock-stubbed FastAPI backend for fishing-route planning, PFZ (Potential Fishing Zone) lookup, storm advisories, and voyage risk assessment near the Indian coastline.

> **Note:** All data returned by this service is **hardcoded mock data** (tagged `"source": "MOCK_DATA"`). Real API integrations, LLM calls, and databases are intentionally out of scope for this initial scaffold.

## Project Structure

```
orca-backend/
  app/
    main.py              # FastAPI app entrypoint
    schemas.py            # Pydantic models
    orchestrator.py       # Keyword-based dispatch logic
    agents/
      __init__.py
      marine_data_agent.py
      weather_agent.py
      pfz_agent.py
      geospatial_agent.py
      risk_agent.py
      reporting_agent.py
  requirements.txt
  .gitignore
  README.md
```

## Setup

```bash
# 1. Create & activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the development server
uvicorn app.main:app --reload
```

The server will start at **http://127.0.0.1:8000**.  
Interactive API docs are available at **http://127.0.0.1:8000/docs**.

## Testing

### Health check

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status": "ok"}
```

### Query endpoint

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d "{\"user_query\": \"is it safe to go fishing near Rameswaram today\"}"
```

This will return a full `RouteRequestState` JSON with mock PFZ zones and storm data populated (because the query contains both "safe" and "fish" keywords).
