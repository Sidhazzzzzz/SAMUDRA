"""Tests for FastAPI INCOIS Layer Proxy (/api/layers/{layer_name}).

Verifies:
1. Proxy routing for sst, chl, eez, sectors, and pfz.
2. Graceful fallback snapshots when live INCOIS is unreachable.
3. Cache status and data source headers (X-Data-Source, X-Cache-Status).
4. Probe endpoint (?probe=1) functionality.
"""

import pytest
from starlette.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_proxy_eez_layer(client):
    """Test fetching EEZ GeoJSON boundary through proxy."""
    response = client.get("/api/layers/eez")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    assert "x-data-source" in response.headers
    assert "x-cache-status" in response.headers

    data = response.json()
    assert "features" in data or "type" in data
    assert data.get("type") in ["FeatureCollection", "Feature"] or len(data.get("features", [])) > 0


def test_proxy_sectors_layer(client):
    """Test fetching Sectors GeoJSON through proxy."""
    response = client.get("/api/layers/sectors")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    
    data = response.json()
    assert "features" in data
    assert len(data["features"]) > 0


def test_proxy_pfz_layer(client):
    """Test fetching PFZ GeoJSON through proxy."""
    response = client.get("/api/layers/pfz")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    
    data = response.json()
    assert "features" in data
    assert len(data["features"]) > 0


def test_proxy_sst_layer(client):
    """Test fetching SST WMS tile through proxy."""
    response = client.get(
        "/api/layers/sst?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=PFZ-TUNA-SST-CHL:sst&BBOX=78,8,80,10&WIDTH=256&HEIGHT=256&SRS=EPSG:4326&FORMAT=image/png"
    )
    assert response.status_code == 200
    assert response.headers.get("content-type") == "image/png"
    assert len(response.content) > 0


def test_proxy_chl_layer(client):
    """Test fetching Chlorophyll WMS tile through proxy."""
    response = client.get(
        "/api/layers/chl?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap&LAYERS=PFZ-TUNA-SST-CHL:chl&BBOX=78,8,80,10&WIDTH=256&HEIGHT=256&SRS=EPSG:4326&FORMAT=image/png"
    )
    assert response.status_code == 200
    assert response.headers.get("content-type") == "image/png"
    assert len(response.content) > 0


def test_proxy_legend_graphic(client):
    """Test fetching legend image through proxy."""
    response = client.get(
        "/api/layers/sst?REQUEST=GetLegendGraphic&VERSION=1.0.0&FORMAT=image/png&LAYER=PFZ-TUNA-SST-CHL:sst"
    )
    assert response.status_code == 200
    assert response.headers.get("content-type") == "image/png"


def test_proxy_probe_endpoint(client):
    """Test probing layer health with ?probe=1."""
    response = client.get("/api/layers/sst?probe=1")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["live", "fallback"]


def test_proxy_unknown_layer(client):
    """Test unknown layer returns 404."""
    response = client.get("/api/layers/nonexistent")
    assert response.status_code == 404
