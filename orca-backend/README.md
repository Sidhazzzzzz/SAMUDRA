# ORCA — Maritime Decision-Support System

A full-stack, AI-powered FastAPI backend and plain JS/HTML/CSS frontend for fishing and commercial route planning, PFZ (Potential Fishing Zone) lookup, storm advisories, and voyage risk assessment near the Indian coastline.

> **Note:** The backend uses real API integrations with INCOIS (GeoServer), Open-Meteo (Marine & Weather APIs), OpenTopoData (GEBCO 2020 bathymetry) and an LLM orchestration layer powered by LangChain (Groq / Google GenAI). If live data is unavailable, local JSON snapshots are used as fallbacks.

## Project Structure

```
ORCA/
  orca-backend/
    app/
      main.py              # FastAPI app entrypoint
      schemas.py           # Pydantic models
      orchestrator.py      # LangChain LLM dispatch logic
      agents/              # Real integrations & tools
        ...
    requirements.txt
    .env                   # Required API Keys
    .gitignore
    README.md
  orca-frontend/
    index.html             # Main UI
    app.js                 # Frontend logic
    style.css              # Styling
```

## Setup & Running

### 1. Backend Setup

```bash
cd orca-backend

# Create & activate a virtual environment
python -m venv venv
# Windows: venv\Scripts\activate
# macOS / Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the `orca-backend` directory with the following keys:
```env
GROQ_API_KEY=your_groq_api_key
GOOGLE_API_KEY=your_google_api_key
```

### 3. Run the Backend Server

```bash
uvicorn app.main:app --reload
```
The server will start at **http://127.0.0.1:8000**.
Interactive API docs are available at **http://127.0.0.1:8000/docs**.

### 4. Run the Frontend
You can serve the frontend with any static file server, for example using Python:
```bash
cd ../orca-frontend
python -m http.server 8080
```
Open **http://127.0.0.1:8080** in your browser.

## Testing Endpoints

### Health check
```bash
curl http://127.0.0.1:8000/health
```

### System Status
```bash
curl http://127.0.0.1:8000/system/status
```
Returns a JSON report checking the live reachability of all external dependencies (Open-Meteo, NOAA ERDDAP, OpenTopoData, etc.) in a single call.

### Query endpoint
```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"user_query": "Is it safe to go fishing near Rameswaram today?"}'
```
This triggers the LangChain agent to select the appropriate tools, fetch real data (PFZ, weather, routing), and return a JSON containing the structured advisory.
