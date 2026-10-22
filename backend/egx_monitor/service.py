"""Pulls data from the active provider, caches it, and shapes it for the dashboard."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime

from .config import Settings
from .market_hours import CAIRO, market_status
from .models import Quote
from .providers import Provider, SimulatedProvider, TradingViewProvider

log = logging.getLogger("egx_monitor")

MIN_MOVER_VALUE = 1_000_000  # EGP traded today


class MarketService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.live: Provider = TradingViewProvider()
        self.sim: Provider = SimulatedProvider()
        self._snapshot: dict | None = None
        self._snapshot_at = 0.0
        self._bars_cache: dict[tuple[str, str], tuple[float, dict]] = {}
        self._lock = asyncio.Lock()
        self.last_error: str | None = None

    # ---- provider selection -------------------------------------------------
    async def _call(self, method: str, *args):
        """Run a provider method according to data_mode, falling back to simulated data in 'auto'."""
        mode = self.settings.data_mode
        if mode != "simulated":
            try:
                result = await getattr(self.live, method)(*args)
                if result:
                    self.last_error = None
                    return result, self.live
                raise RuntimeError("empty response")
            except Exception as exc:  # network down, endpoint changed, …
                self.last_error = f"{type(exc).__name__}: {exc}"
                log.warning("live %s failed: %s", method, self.last_error)
                if mode == "live":
                    raise
        return await getattr(self.sim, method)(*args), self.sim

    # ---- snapshot -----------------------------------------------------------
    def _ttl(self) -> float:
        s = self.settings
        return s.refresh_open if market_status()["isOpen"] else s.refresh_closed

    async def snapshot(self, force: bool = False) -> dict:
        async with self._lock:
            if not force and self._snapshot and time.time() - self._snapshot_at < self._ttl():
                return self._refresh_clock(self._snapshot)
            (stocks, src), (indices, _), (fx, _) = await asyncio.gather(
                self._call("scan_market"), self._call("indices"), self._call("fx")
            )
            self._snapshot = self._build(stocks, indices, fx, src)
            self._snapshot_at = time.time()
            return self._snapshot

    def _refresh_clock(self, snap: dict) -> dict:
        return {**snap, "market": market_status()}

    def _build(self, stocks: list[Quote], indices: list[Quote], fx: list[Quote], src: Provider) -> dict:
        by_symbol = {q.symbol: q for q in stocks}
        priced = [q for q in stocks if q.last is not None and q.changePct is not None]
        traded = [q for q in priced if (q.volume or 0) > 0]
        # Movers lists skip illiquid names, where a handful of shares can print a ±20% move.
        liquid = [q for q in traded if (q.value or 0) >= MIN_MOVER_VALUE] or traded

        watch = [by_symbol[s].to_dict() for s in self.settings.watchlist if s in by_symbol]
        tape = sorted(priced, key=lambda q: q.marketCap or 0, reverse=True)[:30]
        gainers = sorted(liquid, key=lambda q: q.changePct, reverse=True)[:12]
        losers = sorted(liquid, key=lambda q: q.changePct)[:12]
        active = sorted(traded, key=lambda q: q.value or 0, reverse=True)[:12]

        advancers = sum(1 for q in traded if q.changePct > 0)
        decliners = sum(1 for q in traded if q.changePct < 0)

        return {
            "source": {"name": src.name, "live": src.live, "error": self.last_error},
            "market": market_status(),
            "updatedAt": int(time.time()),
            "indices": [q.to_dict() for q in indices],
            "fx": [q.to_dict() for q in fx],
            "watchlist": watch,
            "watchlistSymbols": list(self.settings.watchlist),
            "maxWatchlist": self.settings.max_watchlist,
            "tape": [q.to_dict() for q in tape],
            "gainers": [q.to_dict() for q in gainers],
            "losers": [q.to_dict() for q in losers],
            "active": [q.to_dict() for q in active],
            "sectors": _sector_heat(priced),
            "breadth": {
                "advancers": advancers,
                "decliners": decliners,
                "unchanged": len(traded) - advancers - decliners,
                "listed": len(stocks),
                "turnover": sum(q.value or 0 for q in traded),
            },
            "universe": [{"symbol": q.symbol, "name": q.name} for q in stocks],
        }

    # ---- charts -------------------------------------------------------------
    async def chart(self, symbol: str, range_: str) -> dict:
        key = (symbol, range_)
        cached = self._bars_cache.get(key)
        if cached and time.time() - cached[0] < min(self._ttl(), 60):
            return cached[1]
        bars, src = await self._call("bars", symbol, range_)
        if range_ == "1D" and bars:
            # Keep only the latest session (the request over-fetches to cover a full day).
            last_day = datetime.fromtimestamp(bars[-1].t, CAIRO).date()
            bars = [b for b in bars if datetime.fromtimestamp(b.t, CAIRO).date() == last_day]
        payload = {
            "symbol": symbol,
            "range": range_,
            "source": {"name": src.name, "live": src.live},
            "bars": [asdict(b) for b in bars],
        }
        self._bars_cache[key] = (time.time(), payload)
        return payload

    # ---- watchlist ----------------------------------------------------------
    def set_watchlist(self, symbols: list[str]) -> list[str]:
        clean: list[str] = []
        for s in symbols:
            s = s.strip().upper()
            if s and s not in clean:
                clean.append(s)
        self.settings.watchlist = clean[: self.settings.max_watchlist]
        self.settings.save()
        self._snapshot_at = 0  # rebuild on next request
        return self.settings.watchlist


def _sector_heat(stocks: list[Quote]) -> list[dict]:
    """Market-cap weighted % change per sector (equal weight when caps are missing)."""
    groups: dict[str, list[Quote]] = defaultdict(list)
    for q in stocks:
        groups[q.sector or "Other"].append(q)
    out = []
    for sector, qs in groups.items():
        weights = [q.marketCap or 1.0 for q in qs]
        total = sum(weights)
        chg = sum(q.changePct * w for q, w in zip(qs, weights)) / total
        leader = max(qs, key=lambda q: q.marketCap or 0)
        out.append({
            "sector": sector,
            "changePct": chg,
            "count": len(qs),
            "marketCap": sum(q.marketCap or 0 for q in qs),
            "leader": leader.symbol,
        })
    return sorted(out, key=lambda s: s["marketCap"], reverse=True)
