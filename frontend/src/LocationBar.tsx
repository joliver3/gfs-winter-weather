import { METAR_STATIONS, type MetarStation } from "./metarStations";

interface LocationBarProps {
  selectedStation: MetarStation;
  onSelectStation: (station: MetarStation) => void;
  onGetForecast: () => void;
}

export function LocationBar({
  selectedStation,
  onSelectStation,
  onGetForecast,
}: LocationBarProps) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const station = METAR_STATIONS.find((s) => s.icao === e.target.value);
    if (station) onSelectStation(station);
  };

  return (
    <div className="mt-4 space-y-3">
      <label className="block">
        <span className="block text-xs text-slate-400 mb-1">METAR station</span>
        <select
          value={selectedStation.icao}
          onChange={handleChange}
          className="w-full py-3 px-4 rounded-xl bg-slate-800 border border-slate-600 text-slate-100 focus:ring-2 focus:ring-sky-500 focus:border-sky-500"
        >
          {METAR_STATIONS.map((s) => (
            <option key={s.icao} value={s.icao}>
              {s.icao} – {s.name}
            </option>
          ))}
        </select>
      </label>
      <button
        type="button"
        onClick={onGetForecast}
        className="w-full py-3 px-4 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-medium transition"
      >
        Get forecast (latest complete GFS run)
      </button>
      <p className="text-xs text-slate-500">
        Uses the most recent GFS run that has fully published (typically 6+ hours after init).
      </p>
    </div>
  );
}
