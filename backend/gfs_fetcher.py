"""
Fetch GFS 0.25 deg data from NOAA NOMADS for a single point.
Returns 2m temperature and 6-hourly precipitation for the last 2-3 run inits.
"""

import os
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Any

import httpx
import cfgrib
import numpy as np


NOMADS_BASE = "https://nomads.ncep.noaa.gov/cgi-bin/filter_gfs_0p25.pl"
# Forecast hours to fetch (0..240 every 6h = 41 files per run)
FORECAST_HOURS = list(range(0, 241, 6))
# Runs per day: 00, 06, 12, 18 Z
CYCLES = ["00", "06", "12", "18"]
# How many runs to fetch (2 = last 2 runs)
NUM_RUNS = 3
# Snow threshold: 2m temp <= this (C) we treat as snow
SNOW_TEMP_C = 2.0


def _nomads_dir(date: datetime, cycle: str) -> str:
    """NOMADS directory for GFS 0.25: /gfs.YYYYMMDD/HH/atmos"""
    d = date.strftime("%Y%m%d")
    return f"/gfs.{d}/{cycle}/atmos"


def _nomads_file(cycle: str, fhr: int) -> str:
    """File name: gfs.tHHz.pgrb2.0p25.fXXX"""
    return f"gfs.t{cycle}z.pgrb2.0p25.f{fhr:03d}"


def _box_around(lat: float, lon: float, delta: float = 0.5) -> tuple[float, float, float, float]:
    """Return (leftlon, rightlon, toplat, bottomlat) for a small box. NOMADS accepts negative lon."""
    return (lon - delta, lon + delta, lat + delta, lat - delta)


def _fetch_grib(
    client: httpx.Client,
    date: datetime,
    cycle: str,
    fhr: int,
    leftlon: float,
    rightlon: float,
    toplat: float,
    bottomlat: float,
) -> bytes | None:
    """Download one GRIB2 subset from NOMADS. Returns None on 404 or error."""
    nomads_dir = _nomads_dir(date, cycle)
    file_name = _nomads_file(cycle, fhr)
    # NOMADS filter: use lev_2_m_above_ground (underscores), subregion=on for box
    params = {
        "dir": nomads_dir,
        "file": file_name,
        "var_TMP": "on",
        "var_APCP": "on",
        "lev_2_m_above_ground": "on",
        "lev_surface": "on",
        "subregion": "on",
        "leftlon": leftlon,
        "rightlon": rightlon,
        "toplat": toplat,
        "bottomlat": bottomlat,
    }
    url = NOMADS_BASE
    try:
        r = client.get(url, params=params, timeout=60.0)
        if r.status_code != 200:
            return None
        content = r.content
        # NOMADS may return 200 with HTML error page; reject non-GRIB
        if not content or len(content) < 100:
            return None
        if content.lstrip().startswith((b"<", b"%3C")) or b"<html" in content[:500].lower():
            return None
        return content
    except Exception:
        return None


def probe_nomads(lat: float, lon: float) -> dict[str, Any]:
    """
    Try one NOMADS request (one run, one fhr) and return diagnostics for troubleshooting.
    """
    leftlon, rightlon, toplat, bottomlat = _box_around(lat, lon)
    runs = _list_recent_run_dates(complete_only=False)
    if not runs:
        return {"error": "no run dates", "runs_tried": 0}
    run_date, cycle = runs[0]
    fhr = 6
    with httpx.Client() as client:
        raw = _fetch_grib(
            client, run_date, cycle, fhr,
            leftlon, rightlon, toplat, bottomlat,
        )
    if raw is None:
        # Re-do one request to get status and content info
        nomads_dir = _nomads_dir(run_date, cycle)
        file_name = _nomads_file(cycle, fhr)
        params = {
            "dir": nomads_dir,
            "file": file_name,
            "var_TMP": "on",
            "var_APCP": "on",
            "lev_2_m_above_ground": "on",
            "lev_surface": "on",
            "subregion": "on",
            "leftlon": leftlon,
            "rightlon": rightlon,
            "toplat": toplat,
            "bottomlat": bottomlat,
        }
        try:
            r = httpx.get(NOMADS_BASE, params=params, timeout=30.0)
            content = r.content or b""
            is_html = content.lstrip().startswith((b"<", b"%3C")) or b"<html" in content[:500].lower()
            return {
                "run_tried": f"{run_date.strftime('%Y%m%d')}_{cycle}Z",
                "fhr": fhr,
                "status_code": r.status_code,
                "content_length": len(content),
                "is_grib": r.status_code == 200 and len(content) > 100 and not is_html,
                "response_preview": content[:300].decode("utf-8", errors="replace") if content else "",
            }
        except Exception as e:
            return {"error": str(e), "run_tried": f"{run_date.strftime('%Y%m%d')}_{cycle}Z"}

    # We got raw content; try to parse and report
    parse_error = None
    try:
        parsed = _parse_grib_point(raw, lat, lon)
        if parsed is None:
            parse_error = "parse returned None (no t2m/apcp found)"
        else:
            return {
                "run_tried": f"{run_date.strftime('%Y%m%d')}_{cycle}Z",
                "status": "ok",
                "content_length": len(raw),
                "parsed_keys": list(parsed.keys()),
            }
    except Exception as e:
        parse_error = str(e)
    return {
        "run_tried": f"{run_date.strftime('%Y%m%d')}_{cycle}Z",
        "status_code": 200,
        "content_length": len(raw),
        "is_grib": True,
        "parse_error": parse_error,
    }


def _parse_grib_point(grib_bytes: bytes, lat: float, lon: float) -> dict[str, float] | None:
    """
    Open GRIB2 bytes with cfgrib, extract values at nearest point to (lat, lon).
    cfgrib requires a file path (not BytesIO) to create .idx files.
    """
    if not grib_bytes or len(grib_bytes) < 100:
        return None
    try:
        with tempfile.NamedTemporaryFile(suffix=".grib2", delete=False) as tmp:
            tmp.write(grib_bytes)
            path = tmp.name
        try:
            datasets = cfgrib.open_datasets(path, decode_timedelta=False)
            out: dict[str, float] = {}
            for ds in datasets:
                if not hasattr(ds, "latitude") or not hasattr(ds, "longitude"):
                    continue
                lats = ds.latitude.values
                lons = ds.longitude.values
                if lats.ndim == 2 and lons.ndim == 2:
                    dist = (lats - lat) ** 2 + (np.mod(lons - lon + 180, 360) - 180) ** 2
                    j, i = np.unravel_index(np.argmin(dist), dist.shape)
                else:
                    ji = np.argmin(np.abs(lats - lat))
                    ii = np.argmin(np.abs(np.mod(lons - lon + 180, 360) - 180))
                    j, i = ji, ii
                for v in ds.data_vars:
                    arr = ds[v].values
                    if arr.ndim >= 2:
                        val = float(arr.flat[np.ravel_multi_index((j, i), arr.shape[-2:])])
                    else:
                        val = float(arr)
                    name = str(ds[v].attrs.get("GRIB_shortName", v))
                    if "tmp" in name.lower() or "t" == name.lower():
                        out["t2m"] = val
                    elif "apcp" in name.lower() or "precip" in name.lower():
                        out["apcp"] = val
            return out if out else None
        finally:
            os.unlink(path)
    except Exception:
        return None


# Hours after run init before we consider the run "complete" (GFS typically publishes ~6h after init)
COMPLETE_RUN_HOURS = 6


def _list_recent_run_dates(complete_only: bool = True) -> list[tuple[datetime, str]]:
    """(date, cycle) for recent runs. If complete_only, only include runs published 6+ hours ago."""
    now = datetime.now(timezone.utc)
    out: list[tuple[datetime, str]] = []
    for day_offset in range(2):
        d = now.date() - timedelta(days=day_offset)
        for c in CYCLES:
            init = datetime(d.year, d.month, d.day, int(c), 0, 0, tzinfo=timezone.utc)
            if complete_only and (now - init).total_seconds() / 3600 < COMPLETE_RUN_HOURS:
                continue
            out.append((datetime(d.year, d.month, d.day, tzinfo=timezone.utc), c))
    if not out:
        # Fallback: use all runs from last 2 days if none qualify
        for day_offset in range(2):
            d = now.date() - timedelta(days=day_offset)
            for c in CYCLES:
                out.append((datetime(d.year, d.month, d.day, tzinfo=timezone.utc), c))
    out.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return out[:8]


def fetch_timeseries_for_point(
    lat: float,
    lon: float,
    *,
    client: httpx.Client | None = None,
    complete_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Fetch GFS data for (lat, lon) for the last NUM_RUNS runs.
    Returns a list of run results, each:
      - init_time: ISO datetime of run init
      - cycle: "00"|"06"|"12"|"18"
      - points: list of {valid_time, fhr, t2m_c, apcp_mm, precip_6h_mm}
    precip_6h_mm is derived from APCP difference between consecutive forecast hours.
    """
    leftlon, rightlon, toplat, bottomlat = _box_around(lat, lon)
    runs_to_try = _list_recent_run_dates(complete_only=complete_only)
    result: list[dict[str, Any]] = []
    own_client = client is None
    if own_client:
        client = httpx.Client()

    try:
        for (run_date, cycle) in runs_to_try:
            if len(result) >= NUM_RUNS:
                break
            init_time = datetime(
                run_date.year, run_date.month, run_date.day,
                int(cycle), 0, 0, tzinfo=timezone.utc,
            )
            points: list[dict[str, Any]] = []
            prev_apcp: float | None = None
            for fhr in FORECAST_HOURS:
                raw = _fetch_grib(
                    client, run_date, cycle, fhr,
                    leftlon, rightlon, toplat, bottomlat,
                )
                if raw is None:
                    break
                parsed = _parse_grib_point(raw, lat, lon)
                if parsed is None:
                    break
                t2m_k = parsed.get("t2m")
                apcp = parsed.get("apcp", 0.0)
                if t2m_k is None:
                    break
                t2m_c = float(t2m_k) - 273.15
                valid_time = init_time + timedelta(hours=fhr)
                precip_6h = (apcp - prev_apcp) if prev_apcp is not None else 0.0
                if precip_6h < 0:
                    precip_6h = 0.0
                prev_apcp = apcp
                points.append({
                    "valid_time": valid_time.isoformat(),
                    "fhr": fhr,
                    "t2m_c": round(t2m_c, 2),
                    "apcp_mm": round(apcp, 2),
                    "precip_6h_mm": round(precip_6h, 2),
                })
            if points:
                result.append({
                    "init_time": init_time.isoformat(),
                    "cycle": cycle,
                    "points": points,
                })
    finally:
        if own_client:
            client.close()

    return result
