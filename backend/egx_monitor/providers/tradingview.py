"""Live EGX data from TradingView's public endpoints (no account needed).

* Quotes / market scan: https://scanner.tradingview.com/egypt/scan
* Price bars: the chart websocket, as an anonymous user.

These are unofficial, free endpoints; prices may be delayed. If they change or
go down, the service falls back to the simulated provider automatically.
"""

from __future__ import annotations

import asyncio
import json
import random
import re
import string

import httpx

from ..models import Bar, Quote, finite, pct_change
from .base import FX_SYMBOLS, INDEX_SYMBOLS, RANGES, Provider

SCAN_URL = "https://scanner.tradingview.com/{market}/scan"
WS_URL = "wss://data.tradingview.com/socket.io/websocket"
HEADERS = {"User-Agent": "Mozilla/5.0 (EGX-Monitor)", "Origin": "https://www.tradingview.com"}
COLUMNS = [
    "name", "description", "close", "change", "change_abs", "open", "high", "low",
    "volume", "sector", "market_cap_basic", "type",
]


def _row_to_quote(row: dict, kind: str | None = None, label: str | None = None) -> Quote:
    d = dict(zip(COLUMNS, row["d"]))
    last, chg_abs = finite(d["close"]), finite(d["change_abs"])
    prev = last - chg_abs if last is not None and chg_abs is not None else None
    vol = finite(d["volume"])
    return Quote(
        symbol=d["name"],
        name=label or d["description"] or d["name"],
        last=last,
        change=chg_abs,
        changePct=finite(d["change"]) if prev else pct_change(last, prev),
        open=finite(d["open"]),
        high=finite(d["high"]),
        low=finite(d["low"]),
        prevClose=prev,
        volume=vol,
        value=last * vol if last is not None and vol is not None else None,
        marketCap=finite(d["market_cap_basic"]),
        sector=d["sector"],
        kind=kind or d["type"] or "stock",
    )


class TradingViewProvider(Provider):
    name = "TradingView (delayed)"
    live = True

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=15, headers=HEADERS)

    async def _scan(self, market: str, payload: dict) -> list[dict]:
        r = await self._client.post(SCAN_URL.format(market=market), json=payload)
        r.raise_for_status()
        return r.json().get("data") or []

    async def scan_market(self) -> list[Quote]:
        rows = await self._scan("egypt", {
            "columns": COLUMNS,
            "filter": [{"left": "type", "operation": "equal", "right": "stock"}],
            "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
            "range": [0, 600],
        })
        return [_row_to_quote(r) for r in rows]

    async def indices(self) -> list[Quote]:
        rows = await self._scan("egypt", {
            "columns": COLUMNS,
            "symbols": {"tickers": [f"EGX:{s}" for s in INDEX_SYMBOLS]},
        })
        by_name = {r["d"][0]: r for r in rows}
        return [_row_to_quote(by_name[s], "index", label) for s, label in INDEX_SYMBOLS.items() if s in by_name]

    async def fx(self) -> list[Quote]:
        rows = await self._scan("forex", {
            "columns": COLUMNS,
            "symbols": {"tickers": [f"FX_IDC:{s}" for s in FX_SYMBOLS]},
        })
        by_name = {r["d"][0]: r for r in rows}
        return [_row_to_quote(by_name[s], "fx", label) for s, label in FX_SYMBOLS.items() if s in by_name]

    async def bars(self, symbol: str, range_: str) -> list[Bar]:
        interval, count = RANGES.get(range_, RANGES["1D"])
        return await asyncio.wait_for(_fetch_bars(f"EGX:{symbol}", interval, count), timeout=20)


def _frame(func: str, params: list) -> str:
    msg = json.dumps({"m": func, "p": params}, separators=(",", ":"))
    return f"~m~{len(msg)}~m~{msg}"


async def _fetch_bars(tv_symbol: str, interval: str, count: int) -> list[Bar]:
    import websockets  # imported lazily so the app still starts if it is missing

    session = "cs_" + "".join(random.choices(string.ascii_lowercase, k=12))
    symbol_spec = "=" + json.dumps({"symbol": tv_symbol, "adjustment": "splits"})
    async with websockets.connect(WS_URL, origin="https://www.tradingview.com", open_timeout=15) as ws:
        for func, params in [
            ("set_auth_token", ["unauthorized_user_token"]),
            ("chart_create_session", [session, ""]),
            ("resolve_symbol", [session, "sym_1", symbol_spec]),
            ("create_series", [session, "s1", "s1", "sym_1", interval, count]),
        ]:
            await ws.send(_frame(func, params))

        buffer = ""
        while "series_completed" not in buffer:
            msg = await ws.recv()
            # Answer heartbeats or the server drops us.
            for hb in re.findall(r"~m~\d+~m~(~h~\d+)", msg):
                await ws.send(_frame_raw(hb))
            if "symbol_error" in msg or "critical_error" in msg:
                raise RuntimeError(f"TradingView rejected {tv_symbol}")
            buffer += msg

    match = re.search(r'"s":\[(.*?)\],"ns"', buffer)
    if not match:
        return []
    points = json.loads("[" + match.group(1) + "]")
    out = []
    for p in points:
        t, o, h, l, c, *rest = p["v"]
        out.append(Bar(int(t), o, h, l, c, rest[0] if rest else 0.0))
    return out


def _frame_raw(payload: str) -> str:
    return f"~m~{len(payload)}~m~{payload}"
