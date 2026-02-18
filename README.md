# GFS Winter Weather

Mobile-friendly web app that uses GFS model data to indicate winter weather potential by comparing consecutive 6-hourly runs. Tiered output:

- **> 3 days out** (with run agreement): "Winter weather is possible [date range]"
- **1–3 days out**: Start time, duration, expected snow amount/category
- **< 24 hours**: Final call summary

## Stack

- **Backend**: Python (FastAPI), GFS data from NOAA NOMADS (GRIB2), in-memory cache
- **Frontend**: React, Vite, Tailwind CSS; mobile-first

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173 (proxies `/api` to backend)

### Production

1. Set the frontend API base URL (e.g. env `VITE_API_URL`) and use it in `useForecast.ts` instead of `/api` when not in dev.
2. Build: `npm run build` in frontend; serve `dist/` and ensure `/forecast` is handled by your backend.
3. Backend may need to run in a thread pool for GFS fetch (sync HTTP) to avoid blocking; or use `run_in_executor` in the route.

## Environment

- **Backend**: `GFS_CACHE_TTL_MINUTES` (default 60) – cache TTL for forecast responses.

## Notes

- **GFS data**: The backend uses NOAA NOMADS `filter_gfs_0p25.pl` to pull 2 m temperature and surface APCP for a small lat/lon box. The first request for a location can take 1–2 minutes (many 6-hourly files per run × 2–3 runs). Consider running the fetch in a thread pool in production.
- **cfgrib**: Requires a working ecCodes (or eccodes) install for GRIB2 support. On macOS: `brew install eccodes`; then `pip install cfgrib`.
# gfs-winter-weather
