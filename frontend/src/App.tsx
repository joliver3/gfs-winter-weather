import { useState, useCallback, useRef } from "react";
import { useForecast } from "./useForecast";
import { LocationBar } from "./LocationBar";
import { ForecastPanel } from "./ForecastPanel";
import { DEFAULT_STATION, type MetarStation } from "./metarStations";

export default function App() {
  const [selectedStation, setSelectedStation] = useState<MetarStation>(DEFAULT_STATION);
  const { data, error, loading, fetchForecast } = useForecast();
  const hasFetched = useRef(false);

  const handleGetForecast = useCallback(() => {
    hasFetched.current = true;
    fetchForecast(selectedStation.lat, selectedStation.lon);
  }, [selectedStation, fetchForecast]);

  const handleSelectStation = useCallback((station: MetarStation) => {
    setSelectedStation(station);
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans">
      <header className="pt-6 px-4 pb-4 border-b border-slate-700">
        <h1 className="text-xl font-bold tracking-tight">GFS Winter Weather</h1>
        <p className="text-sm text-slate-400 mt-0.5">
          Model run consistency · Snow potential
        </p>
      </header>

      <main className="p-4 pb-8 max-w-lg mx-auto">
        <LocationBar
          selectedStation={selectedStation}
          onSelectStation={handleSelectStation}
          onGetForecast={handleGetForecast}
        />

        {loading && (
          <div className="mt-6 p-4 rounded-xl bg-slate-800 text-slate-300 text-center">
            Loading GFS data…
          </div>
        )}
        {error && (
          <div className="mt-6 p-4 rounded-xl bg-red-900/40 text-red-200 text-center">
            {error}
          </div>
        )}
        {data && !loading && (
          <ForecastPanel data={data} station={selectedStation} />
        )}
        {!data && !loading && !error && hasFetched.current && (
          <div className="mt-6 p-4 rounded-xl bg-slate-800 text-slate-400 text-center">
            No forecast data. Try again or check the backend.
          </div>
        )}
      </main>
    </div>
  );
}
