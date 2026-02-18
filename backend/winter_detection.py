"""
Winter weather detection: classify 6-hourly points as snow/rain, merge into events,
compute snow amount (10:1 ratio), and assign categorical intensity.
"""

from datetime import datetime, timezone
from typing import Any

from gfs_fetcher import SNOW_TEMP_C

# Snow-to-liquid ratio for snow depth estimate (inches of snow per mm liquid)
SNOW_RATIO = 10.0 / 25.4  # 10:1 in/in, 1 in = 25.4 mm
# Categorical bands (inches snow): trace < 0.5 < light < 3 < moderate < 6 < heavy
SNOW_TRACE = 0.5
SNOW_LIGHT = 3.0
SNOW_MODERATE = 6.0


def _is_winter_precip(t2m_c: float, precip_6h_mm: float) -> bool:
    """True if this 6h window is winter precip (snow/ice) with meaningful precip."""
    if precip_6h_mm < 0.05:  # ~trace
        return False
    return t2m_c <= SNOW_TEMP_C


def _snow_inches(liquid_mm: float) -> float:
    """Convert liquid equivalent (mm) to snow depth (inches) using 10:1."""
    return liquid_mm * SNOW_RATIO


def _categorical(snow_inches: float) -> str:
    if snow_inches < 0.1:
        return "trace"
    if snow_inches < SNOW_TRACE:
        return "trace"
    if snow_inches < SNOW_LIGHT:
        return "light"
    if snow_inches < SNOW_MODERATE:
        return "moderate"
    return "heavy"


def detect_winter_windows(points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    From a run's time series (list of {valid_time, t2m_c, precip_6h_mm}), detect
    winter precip windows and merge adjacent 6h periods into events.
    Returns list of events: {start_time, end_time, duration_hours, snow_inches, category}.
    """
    events: list[dict[str, Any]] = []
    i = 0
    while i < len(points):
        p = points[i]
        if not _is_winter_precip(p["t2m_c"], p["precip_6h_mm"]):
            i += 1
            continue
        start_time = p["valid_time"]
        total_liquid_mm = p["precip_6h_mm"]
        j = i + 1
        while j < len(points) and _is_winter_precip(points[j]["t2m_c"], points[j]["precip_6h_mm"]):
            total_liquid_mm += points[j]["precip_6h_mm"]
            j += 1
        end_time = points[j - 1]["valid_time"] if j > i else start_time
        duration_hours = (j - i) * 6
        snow_inches = round(_snow_inches(total_liquid_mm), 1)
        events.append({
            "start_time": start_time,
            "end_time": end_time,
            "duration_hours": duration_hours,
            "snow_inches": snow_inches,
            "category": _categorical(snow_inches),
        })
        i = j
    return events
