"""EGX trading calendar: Sunday–Thursday, 10:00–14:30 Africa/Cairo."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

CAIRO = ZoneInfo("Africa/Cairo")
SESSION_OPEN = time(10, 0)
SESSION_CLOSE = time(14, 30)
PRE_OPEN = time(9, 30)
# Python weekday(): Mon=0 … Sun=6. EGX trades Sun(6), Mon(0)…Thu(3).
TRADING_DAYS = {6, 0, 1, 2, 3}


def cairo_now() -> datetime:
    return datetime.now(CAIRO)


def market_status(now: datetime | None = None) -> dict:
    now = now or cairo_now()
    t = now.time()
    trading_day = now.weekday() in TRADING_DAYS
    if trading_day and SESSION_OPEN <= t < SESSION_CLOSE:
        state = "OPEN"
    elif trading_day and PRE_OPEN <= t < SESSION_OPEN:
        state = "PRE-OPEN"
    else:
        state = "CLOSED"
    return {
        "state": state,
        "isOpen": state == "OPEN",
        "tradingDay": trading_day,
        "cairoTime": now.strftime("%H:%M:%S"),
        "cairoDate": now.strftime("%a %d %b %Y"),
        "session": f"{SESSION_OPEN:%H:%M}–{SESSION_CLOSE:%H:%M} Cairo, Sun–Thu",
    }
