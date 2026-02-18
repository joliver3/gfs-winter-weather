import type { ForecastResponse, DetailedItem, FinalCallItem } from "./useForecast";
import type { MetarStation } from "./metarStations";

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

interface ForecastPanelProps {
  data: ForecastResponse;
  station?: MetarStation;
}

export function ForecastPanel({ data, station }: ForecastPanelProps) {
  const { possible, detailed, finalCall, last_updated, runs_used, message } =
    data;

  if (message && !possible && !detailed?.length && !finalCall) {
    return (
      <div className="mt-6 p-4 rounded-xl bg-slate-800 text-slate-300">
        {message}
      </div>
    );
  }

  return (
    <div className="mt-6 space-y-4">
      {station && (
        <p className="text-sm text-slate-400">
          Forecast for <strong className="text-slate-300">{station.icao}</strong> – {station.name}
        </p>
      )}
      {last_updated && (
        <p className="text-xs text-slate-500">
          Last updated: {formatTime(last_updated)} · {runs_used} run{runs_used !== 1 ? "s" : ""} used
        </p>
      )}

      {possible && (
        <section className="p-4 rounded-xl bg-slate-800 border border-slate-600">
          <h2 className="text-sm font-semibold text-sky-300 uppercase tracking-wide mb-2">
            Possible winter weather
          </h2>
          <p className="text-slate-200">{possible.message}</p>
          <p className="text-slate-400 text-sm mt-1">{possible.date_range}</p>
        </section>
      )}

      {detailed && detailed.length > 0 && (
        <section className="p-4 rounded-xl bg-slate-800 border border-slate-600">
          <h2 className="text-sm font-semibold text-amber-300 uppercase tracking-wide mb-3">
            Detailed (1–3 days out)
          </h2>
          <ul className="space-y-3">
            {detailed.map((d: DetailedItem, i: number) => (
              <li
                key={i}
                className="pb-3 border-b border-slate-700 last:border-0 last:pb-0"
              >
                <p className="text-slate-200">
                  Start: {formatTime(d.start_time)} · {d.duration_hours}h
                </p>
                <p className="text-slate-300 text-sm mt-1">
                  Snow: {d.snow_inches} in ({d.category})
                </p>
                <p className="text-slate-500 text-xs mt-0.5">
                  ~{Math.round(d.lead_hours / 24)} day(s) from latest run
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {finalCall && (
        <section className="p-4 rounded-xl bg-amber-900/30 border border-amber-600/50">
          <h2 className="text-sm font-semibold text-amber-200 uppercase tracking-wide mb-2">
            Final call (&lt;24 h)
          </h2>
          <p className="text-amber-100 text-sm leading-relaxed">
            {finalCall.message}
          </p>
          <p className="text-amber-200/80 text-xs mt-2">
            {finalCall.snow_inches} in ({finalCall.category}) · {finalCall.duration_hours}h
          </p>
        </section>
      )}

      {!possible && !detailed?.length && !finalCall && (
        <div className="p-4 rounded-xl bg-slate-800 text-slate-400 text-center">
          No winter weather indicated by recent GFS runs for this location.
        </div>
      )}
    </div>
  );
}
