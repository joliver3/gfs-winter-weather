"""
Run consistency and tier logic: compare winter events across GFS runs,
compute lead time, and produce possible / detailed / finalCall payloads.
"""

from datetime import datetime, timezone, timedelta
from typing import Any

from winter_detection import detect_winter_windows

# Lead time thresholds (hours from latest run init to event start)
HOURS_3_DAYS = 72
HOURS_1_DAY = 24
# Runs must agree: at least this many runs show winter weather for same window
MIN_RUNS_AGREEMENT = 2
# Same window = event start times within this many hours
WINDOW_MATCH_HOURS = 18


def _parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _lead_hours(latest_init: datetime, event_start_iso: str) -> float:
    start = _parse_iso(event_start_iso)
    delta = start - latest_init
    return delta.total_seconds() / 3600.0


def _events_agree(events_per_run: list[list[dict]], window_start: str) -> bool:
    """True if at least MIN_RUNS_AGREEMENT runs have an event overlapping this window."""
    window_start_dt = _parse_iso(window_start)
    count = 0
    for run_events in events_per_run:
        for ev in run_events:
            ev_start = _parse_iso(ev["start_time"])
            if abs((ev_start - window_start_dt).total_seconds() / 3600) <= WINDOW_MATCH_HOURS:
                count += 1
                break
    return count >= MIN_RUNS_AGREEMENT


def _merge_run_events(run_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """For each run, detect winter windows. Return list of {init_time, cycle, events}."""
    out = []
    for run in run_results:
        events = detect_winter_windows(run["points"])
        out.append({
            "init_time": run["init_time"],
            "cycle": run["cycle"],
            "events": events,
        })
    return out


def build_tiered_forecast(run_results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    run_results: list from gfs_fetcher.fetch_timeseries_for_point (each has init_time, cycle, points).
    Returns API payload: { possible, detailed, finalCall, last_updated, runs_used }.
    """
    if not run_results:
        return {
            "possible": None,
            "detailed": [],
            "finalCall": None,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "runs_used": 0,
        }

    runs_with_events = _merge_run_events(run_results)
    latest_init = _parse_iso(run_results[0]["init_time"])
    events_per_run = [r["events"] for r in runs_with_events]

    possible: dict[str, Any] | None = None
    detailed: list[dict[str, Any]] = []
    final_call: dict[str, Any] | None = None

    # Collect all unique event windows (by start time) across runs
    all_starts: set[str] = set()
    for r in runs_with_events:
        for ev in r["events"]:
            all_starts.add(ev["start_time"])

    for window_start in sorted(all_starts):
        if not _events_agree(events_per_run, window_start):
            continue
        lead = _lead_hours(latest_init, window_start)
        # Get representative event (from latest run)
        rep = None
        for ev in runs_with_events[0]["events"]:
            if ev["start_time"] == window_start:
                rep = ev
                break
        if rep is None:
            for run_events in runs_with_events:
                for ev in run_events["events"]:
                    ev_start_dt = _parse_iso(ev["start_time"])
                    ws_dt = _parse_iso(window_start)
                    if abs((ev_start_dt - ws_dt).total_seconds() / 3600) <= WINDOW_MATCH_HOURS:
                        rep = ev
                        break
                if rep is not None:
                    break
        if rep is None:
            continue

        if lead > HOURS_3_DAYS:
            if possible is None:
                possible = {
                    "message": "Winter weather is possible.",
                    "date_range": f"{rep['start_time'][:10]} to {rep['end_time'][:10]}",
                }
        elif lead > HOURS_1_DAY:
            detailed.append({
                "start_time": rep["start_time"],
                "end_time": rep["end_time"],
                "duration_hours": rep["duration_hours"],
                "snow_inches": rep["snow_inches"],
                "category": rep["category"],
                "lead_hours": round(lead, 0),
            })
        else:
            final_call = {
                "message": (
                    f"Winter weather event: start {rep['start_time']}, "
                    f"duration {rep['duration_hours']} hours, "
                    f"expected snow {rep['snow_inches']} in ({rep['category']})."
                ),
                "start_time": rep["start_time"],
                "end_time": rep["end_time"],
                "duration_hours": rep["duration_hours"],
                "snow_inches": rep["snow_inches"],
                "category": rep["category"],
            }

    return {
        "possible": possible,
        "detailed": detailed,
        "finalCall": final_call,
        "last_updated": latest_init.isoformat(),
        "runs_used": len(run_results),
    }
