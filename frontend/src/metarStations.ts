/**
 * METAR station codes and coordinates for GFS point forecasts.
 * Default: KDOV (Dover AFB, DE).
 */

export interface MetarStation {
  icao: string;
  name: string;
  lat: number;
  lon: number;
}

export const METAR_STATIONS: MetarStation[] = [
  { icao: "KDOV", name: "Dover AFB, DE", lat: 39.1295, lon: -75.466 },
  { icao: "KPHL", name: "Philadelphia, PA", lat: 39.8729, lon: -75.2437 },
  { icao: "KBWI", name: "Baltimore (BWI), MD", lat: 39.1754, lon: -76.6683 },
  { icao: "KDCA", name: "Washington Reagan, DC", lat: 38.8521, lon: -77.0377 },
  { icao: "KIAD", name: "Washington Dulles, VA", lat: 38.9445, lon: -77.4558 },
  { icao: "KNYC", name: "New York (Central Park)", lat: 40.779, lon: -73.9692 },
  { icao: "KJFK", name: "New York JFK", lat: 40.6398, lon: -73.7789 },
  { icao: "KBOS", name: "Boston, MA", lat: 42.3656, lon: -71.0096 },
  { icao: "KORD", name: "Chicago O'Hare, IL", lat: 41.9742, lon: -87.9073 },
  { icao: "KDEN", name: "Denver, CO", lat: 39.8617, lon: -104.6731 },
];

export const DEFAULT_STATION = METAR_STATIONS[0]; // KDOV

export function getStationByIcao(icao: string): MetarStation | undefined {
  const upper = icao.trim().toUpperCase();
  return METAR_STATIONS.find((s) => s.icao === upper);
}
