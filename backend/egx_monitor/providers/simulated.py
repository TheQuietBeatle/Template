"""Offline fallback: a deterministic random walk around plausible EGX prices.

Used when there is no internet or the live source fails. Everything it returns is
flagged as simulated in the UI.
"""

from __future__ import annotations

import hashlib
import math
import random
from datetime import datetime, timedelta

from ..market_hours import SESSION_CLOSE, SESSION_OPEN, TRADING_DAYS, cairo_now
from ..models import Bar, Quote
from .base import FX_SYMBOLS, INDEX_SYMBOLS, RANGES, Provider

# symbol: (name, sector, base price EGP, shares outstanding in millions)
UNIVERSE = {
    "COMI": ("Commercial International Bank", "Finance", 125.0, 3070),
    "TMGH": ("Talaat Moustafa Group", "Finance", 87.0, 2060),
    "EAST": ("Eastern Company", "Consumer Non-Durables", 33.0, 2230),
    "HRHO": ("EFG Holding", "Finance", 28.5, 1460),
    "ETEL": ("Telecom Egypt", "Communications", 60.0, 1707),
    "SWDY": ("Elsewedy Electric", "Producer Manufacturing", 78.0, 2180),
    "ABUK": ("Abu Qir Fertilizers", "Process Industries", 55.0, 1260),
    "FWRY": ("Fawry", "Technology Services", 13.5, 3400),
    "ORAS": ("Orascom Construction", "Industrial Services", 390.0, 110),
    "EFIH": ("e-finance", "Technology Services", 21.0, 1780),
    "ESRS": ("Ezz Steel", "Non-Energy Minerals", 120.0, 543),
    "MFPC": ("Misr Fertilizers (MOPCO)", "Process Industries", 40.0, 2290),
    "AMOC": ("Alexandria Mineral Oils", "Energy Minerals", 8.2, 1290),
    "PHDC": ("Palm Hills Development", "Finance", 8.5, 3100),
    "OCDI": ("SODIC", "Finance", 26.0, 356),
    "MASR": ("Madinet Masr", "Finance", 5.6, 2050),
    "HELI": ("Heliopolis Housing", "Finance", 7.4, 1340),
    "JUFO": ("Juhayna Food", "Consumer Non-Durables", 26.0, 941),
    "CIEB": ("Credit Agricole Egypt", "Finance", 23.0, 1250),
    "ADIB": ("Abu Dhabi Islamic Bank Egypt", "Finance", 32.0, 500),
    "CLHO": ("Cleopatra Hospitals", "Health Services", 9.5, 1600),
    "ISPH": ("Ibnsina Pharma", "Distribution Services", 3.6, 1050),
    "ORWE": ("Oriental Weavers", "Consumer Durables", 21.0, 665),
    "SKPC": ("Sidi Kerir Petrochemicals", "Process Industries", 21.5, 756),
    "EMFD": ("Emaar Misr", "Finance", 7.9, 4530),
    "BTFH": ("Beltone Holding", "Finance", 3.1, 7080),
    "ALCN": ("Alexandria Containers", "Transportation", 20.0, 2980),
    "CCAP": ("Qalaa Holdings", "Finance", 3.2, 1820),
    "GBCO": ("GB Corp", "Retail Trade", 21.0, 1090),
    "RAYA": ("Raya Holding", "Retail Trade", 3.4, 2120),
    "EGAL": ("Egypt Aluminum", "Non-Energy Minerals", 190.0, 412),
    "ARCC": ("Arabian Cement", "Non-Energy Minerals", 41.0, 379),
    "TALM": ("Taaleem Management", "Consumer Services", 9.0, 730),
    "VLMR": ("Valmore Holding", "Finance", 1.0, 3000),
}
INDEX_BASE = {"EGX30": 51000.0, "EGX30CAPPED": 63300.0, "EGX70EWI": 17100.0, "EGX100EWI": 23000.0}
FX_BASE = {"USDEGP": 48.6, "EUREGP": 56.5, "GBPEGP": 65.0}


def _rng(*parts) -> random.Random:
    seed = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return random.Random(int(seed[:16], 16))


def _last_session_day(now: datetime) -> datetime:
    d = now
    while d.weekday() not in TRADING_DAYS or (d.date() == now.date() and now.time() < SESSION_OPEN):
        d = (d - timedelta(days=1)).replace(hour=SESSION_CLOSE.hour, minute=SESSION_CLOSE.minute)
    return d


def _path(symbol: str, base: float, day: datetime, vol: float) -> tuple[float, list[float]]:
    """Previous close and one price per minute of the session for `day`."""
    r = _rng(symbol, day.date())
    prev = base * math.exp(r.gauss(0, vol * 3))
    minutes = (SESSION_CLOSE.hour * 60 + SESSION_CLOSE.minute) - (SESSION_OPEN.hour * 60 + SESSION_OPEN.minute)
    drift = r.gauss(0, vol / 400)
    price, out = prev * (1 + r.gauss(0, vol / 3)), []
    for _ in range(minutes):
        price *= math.exp(drift + r.gauss(0, vol / 12))
        out.append(price)
    return prev, out


def _session_progress(now: datetime, day: datetime) -> int:
    if day.date() != now.date():
        return 10_000
    start = now.replace(hour=SESSION_OPEN.hour, minute=SESSION_OPEN.minute, second=0, microsecond=0)
    return max(1, int((now - start).total_seconds() // 60) + 1)


class SimulatedProvider(Provider):
    name = "Simulated"
    live = False

    def _quote(self, symbol, name, base, vol, kind, sector=None, shares=None) -> Quote:
        now = cairo_now()
        day = _last_session_day(now)
        prev, path = _path(symbol, base, day, vol)
        seen = path[: _session_progress(now, day)]
        last = round(seen[-1], 2 if base < 1000 else 1)
        volume = float(int(_rng(symbol, day.date(), "v").uniform(2e5, 8e6) * len(seen) / len(path))) if kind == "stock" else None
        return Quote(
            symbol=symbol, name=name, last=last,
            change=round(last - prev, 3), changePct=(last - prev) / prev * 100,
            open=round(seen[0], 3), high=round(max(seen), 3), low=round(min(seen), 3),
            prevClose=round(prev, 3), volume=volume,
            value=last * volume if volume else None,
            marketCap=last * shares * 1e6 if shares else None,
            sector=sector, kind=kind,
        )

    async def scan_market(self) -> list[Quote]:
        return [self._quote(s, n, b, 0.012, "stock", sec, sh) for s, (n, sec, b, sh) in UNIVERSE.items()]

    async def indices(self) -> list[Quote]:
        return [self._quote(s, INDEX_SYMBOLS[s], b, 0.006, "index") for s, b in INDEX_BASE.items()]

    async def fx(self) -> list[Quote]:
        return [self._quote(s, FX_SYMBOLS[s], b, 0.0008, "fx") for s, b in FX_BASE.items()]

    async def bars(self, symbol: str, range_: str) -> list[Bar]:
        interval, count = RANGES.get(range_, RANGES["1D"])
        base = UNIVERSE.get(symbol, (None, None, INDEX_BASE.get(symbol, 50.0), None))[2]
        now = cairo_now()
        if interval == "D":
            r, price, bars = _rng(symbol, "daily", now.date()), base * 0.8, []
            day = now - timedelta(days=count * 1.5)
            while len(bars) < count:
                day += timedelta(days=1)
                if day.weekday() not in TRADING_DAYS:
                    continue
                o = price
                c = o * math.exp(r.gauss(0.0015, 0.018))
                h, l = max(o, c) * (1 + abs(r.gauss(0, 0.007))), min(o, c) * (1 - abs(r.gauss(0, 0.007)))
                ts = int(day.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
                bars.append(Bar(ts, o, h, l, c, r.uniform(1e6, 9e6)))
                price = c
            return bars
        step = int(interval)
        day = _last_session_day(now)
        _, path = _path(symbol, base, day, 0.006 if symbol in INDEX_BASE else 0.012)
        path = path[: _session_progress(now, day)]
        start = day.replace(hour=SESSION_OPEN.hour, minute=SESSION_OPEN.minute, second=0, microsecond=0)
        r = _rng(symbol, day.date(), "bars")
        bars = []
        for i in range(0, len(path), step):
            chunk = path[i : i + step]
            ts = int((start + timedelta(minutes=i)).timestamp())
            bars.append(Bar(ts, chunk[0], max(chunk), min(chunk), chunk[-1], r.uniform(2e4, 3e5)))
        return bars[-count:]


