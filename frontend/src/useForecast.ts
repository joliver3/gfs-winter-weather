import { useState, useCallback } from "react";

export interface PossibleItem {
  message: string;
  date_range: string;
}

export interface DetailedItem {
  start_time: string;
  end_time: string;
  duration_hours: number;
  snow_inches: number;
  category: string;
  lead_hours: number;
}

export interface FinalCallItem {
  message: string;
  start_time: string;
  end_time: string;
  duration_hours: number;
  snow_inches: number;
  category: string;
}

export interface ForecastResponse {
  possible: PossibleItem | null;
  detailed: DetailedItem[];
  finalCall: FinalCallItem | null;
  last_updated: string | null;
  runs_used: number;
  lat?: number;
  lon?: number;
  message?: string;
}

export function useForecast() {
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchForecast = useCallback(async (lat: number, lon: number) => {
    setLoading(true);
    setError(null);
    try {
      const base =
        import.meta.env.DEV
          ? "/api"
          : (import.meta.env.VITE_API_URL ?? "");
      const r = await fetch(
        `${base}/forecast?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}&complete_only=1`
      );
      if (!r.ok) {
        const t = await r.text();
        throw new Error(t || `HTTP ${r.status}`);
      }
      const json: ForecastResponse = await r.json();
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, error, loading, fetchForecast };
}
