"""
GFS Winter Weather API: GET /forecast?lat=&lon= returns tiered winter forecast.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from gfs_fetcher import fetch_timeseries_for_point, probe_nomads
from tiers import build_tiered_forecast

# In-memory cache: key = (round(lat,2), round(lon,2)), value = { run_results, tiered }
_cache: dict[tuple[float, float], tuple[list, dict]] = {}
_cache_ttl_seconds = settings.gfs_cache_ttl_minutes * 60
_cache_times: dict[tuple[float, float], float] = {}


def _get_cached(lat: float, lon: float):
    import time
    key = (round(lat, 2), round(lon, 2))
    if key not in _cache or key not in _cache_times:
        return None
    if time.time() - _cache_times[key] > _cache_ttl_seconds:
        del _cache[key]
        del _cache_times[key]
        return None
    return _cache[key][1]  # tiered payload


def _set_cached(lat: float, lon: float, run_results: list, tiered: dict):
    import time
    key = (round(lat, 2), round(lon, 2))
    _cache[key] = (run_results, tiered)
    _cache_times[key] = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    _cache.clear()
    _cache_times.clear()


app = FastAPI(
    title="GFS Winter Weather API",
    description="Tiered winter weather forecast from GFS model run consistency.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/forecast")
def get_forecast(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    use_cache: bool = Query(True, description="Use cached result if available"),
    complete_only: bool = Query(True, description="Use only latest complete GFS runs (6+ hours after init)"),
):
    """
    Return tiered winter weather forecast for (lat, lon).
    - possible: >3 days out, runs agree → "Winter weather is possible [date range]"
    - detailed: 24h–72h out → start, duration, snow amount/category
    - finalCall: <24h out → final call message
    """
    if use_cache:
        cached = _get_cached(lat, lon)
        if cached is not None:
            payload = {**cached, "lat": lat, "lon": lon}
            return JSONResponse(
                content=payload,
                headers={"Cache-Control": "public, max-age=600"},
            )

    try:
        run_results = fetch_timeseries_for_point(lat, lon, complete_only=complete_only)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GFS fetch failed: {e!s}")

    if not run_results:
        return JSONResponse(
            content={
                "possible": None,
                "detailed": [],
                "finalCall": None,
                "last_updated": None,
                "runs_used": 0,
                "lat": lat,
                "lon": lon,
                "message": (
                    "No GFS runs available for this location. "
                    "Runs may not be published yet, or GRIB parsing failed (ensure ecCodes is installed: brew install eccodes)."
                ),
            },
            headers={"Cache-Control": "public, max-age=60"},
        )

    tiered = build_tiered_forecast(run_results)
    tiered["lat"] = lat
    tiered["lon"] = lon
    _set_cached(lat, lon, run_results, tiered)
    return JSONResponse(
        content=tiered,
        headers={"Cache-Control": "public, max-age=600"},
    )


@app.get("/forecast/debug")
def forecast_debug(
    lat: float = Query(39.1295, ge=-90, le=90),
    lon: float = Query(-75.466, ge=-180, le=180),
):
    """
    Run one NOMADS request and return status/content/parse diagnostics for troubleshooting.
    """
    try:
        return probe_nomads(lat, lon)
    except Exception as e:
        return {"error": str(e)}


@app.get("/health")
def health():
    return {"status": "ok"}
