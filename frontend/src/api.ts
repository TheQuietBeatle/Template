import type { ChartData, Snapshot } from "./types";

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  snapshot: (force = false) => json<Snapshot>(`/api/snapshot${force ? "?force=true" : ""}`),
  chart: (symbol: string, range: string) =>
    json<ChartData>(`/api/chart/${encodeURIComponent(symbol)}?range=${range}`),
  brief: (kind: string) => json<{ kind: string; text: string }>(`/api/brief?kind=${kind}`),
  setWatchlist: (symbols: string[]) =>
    json<{ watchlist: string[] }>("/api/watchlist", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbols }),
    }),
  setTheme: (theme: string) =>
    json("/api/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ theme }),
    }),
  settings: () => json<{ theme: string; data_mode: string }>("/api/settings"),
};
