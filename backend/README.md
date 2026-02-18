# GFS Winter Weather – Backend

Python FastAPI service that fetches GFS data from NOAA NOMADS, detects winter weather windows, and returns tiered forecasts.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

## Environment

- `GFS_CACHE_TTL_MINUTES` (optional): cache TTL for GFS data, default 60.
