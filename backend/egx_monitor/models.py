"""Plain data shapes shared by providers and the API."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass


def finite(x) -> float | None:
    """Return x as a float, or None if it is missing/NaN/Infinity (avoids '+Infinity%' in the UI)."""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def pct_change(last, prev) -> float | None:
    last, prev = finite(last), finite(prev)
    if last is None or not prev:
        return None
    return finite((last - prev) / prev * 100)


@dataclass
class Quote:
    symbol: str
    name: str
    last: float | None
    change: float | None = None
    changePct: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    prevClose: float | None = None
    volume: float | None = None
    value: float | None = None  # traded value in EGP (last * volume)
    marketCap: float | None = None
    sector: str | None = None
    kind: str = "stock"

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: (finite(v) if isinstance(v, float) else v) for k, v in d.items()}


@dataclass
class Bar:
    t: int  # unix seconds
    o: float
    h: float
    l: float
    c: float
    v: float
