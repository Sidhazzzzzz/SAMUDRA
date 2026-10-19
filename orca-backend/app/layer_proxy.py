"""Layer proxy for INCOIS GeoServer WMS/WFS layers with disk caching and graceful fallback.

Proxies requests for SST, Chlorophyll, EEZ, Sectors, and PFZ layers.
When live INCOIS fetches fail or time out, it serves disk-cached responses
or bundled fallback snapshots with X-Data-Source: fallback and X-Cache-Status headers,
so the frontend can display CACHED / FALLBACK badges instead of broken layers.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
import time
import httpx

logger = logging.getLogger("orca.layer_proxy")

DATA_DIR = Path(__file__).resolve().parent / "data"
FALLBACK_DIR = DATA_DIR / "fallback"
LAYER_CACHE_DIR = DATA_DIR / "cache" / "layers"
LAYER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

INCOIS_BASE_WMS = "https://incois.gov.in/geoserver/PFZ-TUNA-SST-CHL/wms"
INCOIS_EEZ_WFS = "https://incois.gov.in/geoserver/PFZ_EEZ/wfs"
INCOIS_SECTORS_WFS = "https://incois.gov.in/geoserver/PFZ_Sectors/wfs"
INCOIS_PFZ_WFS = "https://incois.gov.in/geoserver/PFZ_Automation/wfs"

HEADERS = {
    "User-Agent": "SAMUDRA-Maritime-Advisory/1.0 (contact: sidharthakedlayah@gmail.com)",
}

# In-memory circuit breaker to avoid tile latency during upstream outages
_CIRCUIT_DOWNTIME: dict[str, float] = {}

def _should_skip_upstream(layer_name: str) -> bool:
    last_failed = _CIRCUIT_DOWNTIME.get(layer_name)
    if last_failed and (time.time() - last_failed < 60.0):
        return True
    return False

def _record_upstream_failure(layer_name: str):
    _CIRCUIT_DOWNTIME[layer_name] = time.time()

def _record_upstream_success(layer_name: str):
    _CIRCUIT_DOWNTIME.pop(layer_name, None)


def _cache_key(layer_name: str, params: dict[str, Any]) -> str:
    sorted_items = sorted((str(k).lower(), str(v)) for k, v in params.items() if k.lower() != "probe")
    query_str = "&".join(f"{k}={v}" for k, v in sorted_items)
    digest = hashlib.sha256(query_str.encode("utf-8")).hexdigest()[:16]
    return f"{layer_name}_{digest}"


async def proxy_layer_request(layer_path: str, request: Request) -> Response:
    """Handle a proxied layer request."""
    # Normalize layer name
    clean_path = layer_path.strip("/").lower()
    layer_name = clean_path.split("/")[0]
    subpath = clean_path.split("/")[1] if "/" in clean_path else ""

    params = dict(request.query_params)
    is_probe = "probe" in params
    if is_probe:
        params.pop("probe", None)

    # Determine layer type and upstream target
    is_raster = layer_name in ("sst", "chl")
    is_legend = params.get("REQUEST", "").lower() == "getlegendgraphic" or params.get("request", "").lower() == "getlegendgraphic"

    if layer_name == "sst":
        upstream_url = INCOIS_BASE_WMS
        if is_legend:
            params.setdefault("REQUEST", "GetLegendGraphic")
            params.setdefault("VERSION", "1.0.0")
            params.setdefault("FORMAT", "image/png")
            params.setdefault("LAYER", "PFZ-TUNA-SST-CHL:sst")
            params.setdefault("LEGEND_OPTIONS", "fontAntiAliasing:true;dpi:120")
        else:
            params.setdefault("SERVICE", "WMS")
            params.setdefault("VERSION", "1.1.1")
            params.setdefault("REQUEST", "GetMap")
            params.setdefault("LAYERS", "PFZ-TUNA-SST-CHL:sst")
            params.setdefault("FORMAT", "image/png")
            params.setdefault("TRANSPARENT", "true")

    elif layer_name == "chl":
        upstream_url = INCOIS_BASE_WMS
        if is_legend:
            params.setdefault("REQUEST", "GetLegendGraphic")
            params.setdefault("VERSION", "1.0.0")
            params.setdefault("FORMAT", "image/png")
            params.setdefault("LAYER", "PFZ-TUNA-SST-CHL:chl")
            params.setdefault("LEGEND_OPTIONS", "fontAntiAliasing:true;dpi:120")
        else:
            params.setdefault("SERVICE", "WMS")
            params.setdefault("VERSION", "1.1.1")
            params.setdefault("REQUEST", "GetMap")
            params.setdefault("LAYERS", "PFZ-TUNA-SST-CHL:chl")
            params.setdefault("FORMAT", "image/png")
            params.setdefault("TRANSPARENT", "true")

    elif layer_name == "eez":
        upstream_url = INCOIS_EEZ_WFS
        params.setdefault("SERVICE", "WFS")
        params.setdefault("VERSION", "1.1.0")
        params.setdefault("REQUEST", "GetFeature")
        params.setdefault("TYPENAME", "PFZ_EEZ:indiaeez")
        params.setdefault("outputFormat", "application/json")

    elif layer_name == "sectors":
        upstream_url = INCOIS_SECTORS_WFS
        params.setdefault("SERVICE", "WFS")
        params.setdefault("VERSION", "1.1.0")
        params.setdefault("REQUEST", "GetFeature")
        params.setdefault("TYPENAME", "PFZ_Sectors:sector_new")
        params.setdefault("outputFormat", "application/json")

    elif layer_name == "pfz":
        upstream_url = INCOIS_PFZ_WFS
        params.setdefault("SERVICE", "WFS")
        params.setdefault("VERSION", "1.1.0")
        params.setdefault("REQUEST", "GetFeature")
        params.setdefault("TYPENAME", "PFZ_Automation:pfzlines")
        params.setdefault("outputFormat", "application/json")

    else:
        return JSONResponse(
            status_code=404,
            content={"error": f"Unknown layer: {layer_name}. Supported: sst, chl, eez, sectors, pfz"},
        )

    # If it's a health probe for the layer
    if is_probe:
        try:
            probe_url = upstream_url
            probe_params = {"SERVICE": "WMS", "REQUEST": "GetCapabilities"} if is_raster else {"SERVICE": "WFS", "REQUEST": "GetCapabilities"}
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(probe_url, params=probe_params, headers=HEADERS)
                if resp.status_code == 200:
                    return JSONResponse(
                        content={"status": "live", "layer": layer_name},
                        headers={
                            "X-Data-Source": "live",
                            "X-Cache-Status": "LIVE",
                            "Access-Control-Expose-Headers": "X-Data-Source, X-Cache-Status",
                        },
                    )
        except Exception:
            pass

        return JSONResponse(
            content={"status": "fallback", "layer": layer_name, "is_fallback": True},
            headers={
                "X-Data-Source": "fallback",
                "X-Cache-Status": "FALLBACK",
                "Access-Control-Expose-Headers": "X-Data-Source, X-Cache-Status",
            },
        )

    # Determine cache file path
    ext = "png" if (is_raster or is_legend) else "json"
    key = _cache_key(layer_name, params)
    cache_path = LAYER_CACHE_DIR / f"{key}.{ext}"

    # Try live fetch from INCOIS
    live_content = None
    media_type = "image/png" if ext == "png" else "application/json"
    fetch_error = None

    if not _should_skip_upstream(layer_name):
        try:
            async with httpx.AsyncClient(timeout=2.5, verify=False) as client:
                resp = await client.get(upstream_url, params=params, headers=HEADERS)
                if resp.status_code == 200 and len(resp.content) > 0:
                    live_content = resp.content
                    media_type = resp.headers.get("content-type", media_type)
                    _record_upstream_success(layer_name)
                else:
                    fetch_error = f"HTTP {resp.status_code}"
                    _record_upstream_failure(layer_name)
        except Exception as exc:
            fetch_error = str(exc)
            _record_upstream_failure(layer_name)
    else:
        fetch_error = "Circuit open (upstream marked down)"

    if live_content is not None:
        # Cache successful response to disk
        try:
            with open(cache_path, "wb") as f:
                f.write(live_content)
        except Exception as e:
            logger.warning("Failed to write layer cache for %s: %e", cache_path, e)

        return Response(
            content=live_content,
            media_type=media_type,
            headers={
                "X-Data-Source": "live",
                "X-Cache-Status": "LIVE",
                "Access-Control-Expose-Headers": "X-Data-Source, X-Cache-Status",
            },
        )

    # Live fetch failed: Fallback to disk cache or baseline snapshot
    logger.warning("Live fetch failed for layer '%s' (%s), serving fallback snapshot", layer_name, fetch_error)

    # 1. Check local disk cache from previous successful fetch
    if cache_path.exists():
        try:
            with open(cache_path, "rb") as f:
                cached_bytes = f.read()

            if ext == "json":
                try:
                    data = json.loads(cached_bytes.decode("utf-8"))
                    source_str = f"LOCAL_FALLBACK_SNAPSHOT (cached disk response, live fetch failed: {fetch_error})"
                    if layer_name == "pfz" and "pfz_lines" in data and "type" not in data:
                        data = {
                            "type": "FeatureCollection",
                            "features": data["pfz_lines"],
                            "totalFeatures": len(data["pfz_lines"]),
                            "is_fallback": True,
                            "source": source_str,
                        }
                    else:
                        data["is_fallback"] = True
                        data["source"] = source_str
                    cached_bytes = json.dumps(data).encode("utf-8")
                except Exception:
                    pass

            return Response(
                content=cached_bytes,
                media_type=media_type,
                headers={
                    "X-Data-Source": "fallback",
                    "X-Cache-Status": "CACHED",
                    "Access-Control-Expose-Headers": "X-Data-Source, X-Cache-Status",
                },
            )
        except Exception as e:
            logger.error("Failed to read disk cache for %s: %e", cache_path, e)

    # 2. Check bundled fallback snapshots
    fallback_file = None
    if layer_name == "eez":
        fallback_file = FALLBACK_DIR / "eez_fallback_snapshot.json"
    elif layer_name == "sectors":
        fallback_file = FALLBACK_DIR / "sectors_fallback_snapshot.json"
    elif layer_name == "pfz":
        fallback_file = FALLBACK_DIR / "pfz_fallback_snapshot.json"
    elif layer_name == "sst":
        fallback_file = (FALLBACK_DIR / "sst_legend.png") if is_legend else (FALLBACK_DIR / "sst_fallback_tile.png")
    elif layer_name == "chl":
        fallback_file = (FALLBACK_DIR / "chl_legend.png") if is_legend else (FALLBACK_DIR / "chl_fallback_tile.png")

    if fallback_file and fallback_file.exists():
        with open(fallback_file, "rb") as f:
            fb_bytes = f.read()

        if ext == "json":
            try:
                data = json.loads(fb_bytes.decode("utf-8"))
                source_str = f"LOCAL_FALLBACK_SNAPSHOT (bundled snapshot, live fetch failed: {fetch_error})"
                if layer_name == "pfz" and "pfz_lines" in data and "type" not in data:
                    data = {
                        "type": "FeatureCollection",
                        "features": data["pfz_lines"],
                        "totalFeatures": len(data["pfz_lines"]),
                        "is_fallback": True,
                        "source": source_str,
                    }
                else:
                    data["is_fallback"] = True
                    data["source"] = source_str
                fb_bytes = json.dumps(data).encode("utf-8")
            except Exception:
                pass

        return Response(
            content=fb_bytes,
            media_type=media_type,
            headers={
                "X-Data-Source": "fallback",
                "X-Cache-Status": "FALLBACK",
                "Access-Control-Expose-Headers": "X-Data-Source, X-Cache-Status",
            },
        )

    # 3. Last-resort fallback for raster: 1x1 transparent PNG
    if ext == "png":
        transparent_png_1x1 = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05"
            b"\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return Response(
            content=transparent_png_1x1,
            media_type="image/png",
            headers={
                "X-Data-Source": "fallback",
                "X-Cache-Status": "FALLBACK",
                "Access-Control-Expose-Headers": "X-Data-Source, X-Cache-Status",
            },
        )

    return JSONResponse(
        status_code=503,
        content={"error": f"Layer {layer_name} unavailable and no fallback found.", "is_fallback": True},
        headers={
            "X-Data-Source": "fallback",
            "X-Cache-Status": "FALLBACK",
            "Access-Control-Expose-Headers": "X-Data-Source, X-Cache-Status",
        },
    )
