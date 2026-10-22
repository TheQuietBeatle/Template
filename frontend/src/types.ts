// Shapes returned by the Python API (backend/egx_monitor).

export interface Quote {
  symbol: string;
  name: string;
  last: number | null;
  change: number | null;
  changePct: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  prevClose: number | null;
  volume: number | null;
  value: number | null;
  marketCap: number | null;
  sector: string | null;
  kind: "stock" | "index" | "fx" | string;
}

export interface Sector {
  sector: string;
  changePct: number;
  count: number;
  marketCap: number;
  leader: string;
}

export interface MarketStatus {
  state: "OPEN" | "PRE-OPEN" | "CLOSED";
  isOpen: boolean;
  tradingDay: boolean;
  cairoTime: string;
  cairoDate: string;
  session: string;
}

export interface Snapshot {
  source: { name: string; live: boolean; error: string | null };
  market: MarketStatus;
  updatedAt: number;
  indices: Quote[];
  fx: Quote[];
  watchlist: Quote[];
  watchlistSymbols: string[];
  maxWatchlist: number;
  tape: Quote[];
  gainers: Quote[];
  losers: Quote[];
  active: Quote[];
  sectors: Sector[];
  breadth: { advancers: number; decliners: number; unchanged: number; listed: number; turnover: number };
  universe: { symbol: string; name: string }[];
}

export interface Bar {
  t: number;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

export interface ChartData {
  symbol: string;
  range: string;
  source: { name: string; live: boolean };
  bars: Bar[];
}
