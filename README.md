# EGX Monitor

A desktop dashboard for the **Egyptian Exchange (EGX)**. It opens in its own window when you log in to your laptop
and shows live (delayed) EGX data: indices, your watchlist, intraday charts, sector heat, top movers, market
breadth, EGP exchange rates and an auto-written market brief.

- **Backend:** Python (FastAPI) fetches and shapes the data and runs the desktop window (pywebview).
- **Frontend:** TypeScript + Vite, charts by TradingView Lightweight Charts.

## Setup (one time)

You need **Python 3.10+** and **Node.js 18+**.

| OS | Run |
| --- | --- |
| Windows | double-click `setup.bat` |
| macOS / Linux | `./setup.sh` |

Setup does three things:

1. creates `backend/.venv` and installs the Python packages,
2. builds the dashboard (`frontend` → `backend/egx_monitor/static`),
3. adds an **EGX Monitor** icon to your desktop and makes it **start automatically at login**.

To turn off start-at-login and remove the desktop icon:

```sh
backend/.venv/bin/python scripts/autostart.py uninstall     # macOS / Linux
backend\.venv\Scripts\python scripts\autostart.py uninstall  # Windows
```

## Running it

- Double-click the desktop icon, or run `run.bat` / `./run.sh`.
- `run.sh --browser` opens it in your normal browser instead of a separate window.
- `run.sh --windowed` starts in a normal window instead of maximized.

## What's on screen

| Area | Contents |
| --- | --- |
| Header | EGX 30, EGX 30 Capped, EGX 70 EWI, EGX 100 EWI (click one to chart it), data-source chip, market status, Cairo clock, light/dark toggle |
| Ticker tape | Largest EGX companies by market cap |
| Left | Watchlist (add by ticker or company name, hover a row and click × to remove), EGP FX tab (USD/EUR/GBP) |
| Center | Price chart (1D / 1W / 1M / 6M / 1Y) with volume, VWAP (intraday) or 20-bar average, and previous-close line; sector heat map weighted by market cap (click a tile to chart its biggest company) |
| Right | Gainers / losers / most active by traded value / breadth, and the market analysis panel |

Market hours are Sunday–Thursday 10:00–14:30 Cairo time. While the market is open the dashboard refreshes every
15 seconds; when it's closed it refreshes every few minutes.

## Where the data comes from

`backend/egx_monitor/providers/tradingview.py` reads TradingView's public, no-login endpoints:
the market scanner (`scanner.tradingview.com/egypt/scan`) for quotes and the chart websocket for price bars.
These are **unofficial and delayed**, and could change without notice.

If the live source fails (no internet, endpoint changed), the app falls back to `providers/simulated.py` and the
header chip turns orange: **"Data shown is simulated"**. Hover the chip to see the error.

Want a different feed (a broker API, EGX's paid feed, …)? Subclass `Provider` in
`backend/egx_monitor/providers/base.py` and use it in `service.py`.

The **Market Analysis** panel is rule-based (`backend/egx_monitor/brief.py`): it writes sentences from the numbers on
screen and never calls an AI service, so it can't invent prices. Nothing here is investment advice.

## Settings

Your settings are stored in `~/.egx-monitor/config.json` (outside the repo, so pulling updates won't reset them):

```json
{
  "watchlist": ["COMI", "TMGH", "EAST"],
  "max_watchlist": 25,
  "data_mode": "auto",
  "refresh_open": 15,
  "refresh_closed": 300,
  "theme": "dark"
}
```

`data_mode` is `auto` (live, fall back to simulated), `live` (live only) or `simulated`.

## Editing the code

```
backend/
  egx_monitor/
    __main__.py        starts the server + desktop window
    server.py          API routes (/api/snapshot, /api/chart/{symbol}, /api/brief, /api/watchlist, /api/settings)
    service.py         caching, live→simulated fallback, movers, sector heat, breadth
    brief.py           market brief / sector read / risk notes text
    market_hours.py    EGX trading calendar
    config.py          user settings + default watchlist
    providers/         data sources (tradingview.py, simulated.py)
frontend/
  index.html           page layout
  src/main.ts          rendering + interactions
  src/chart.ts         price/volume chart
  src/style.css        theme colors (CSS variables at the top) and layout
scripts/autostart.py   desktop icon + start-at-login (Windows / macOS / Linux)
```

Development loop with hot reload:

```sh
# terminal 1 – API
cd backend && .venv/bin/python -m egx_monitor --server-only
# terminal 2 – dashboard at http://localhost:5173
cd frontend && npm run dev
```

After changing the frontend, run `npm run build` in `frontend/` so the desktop app picks it up.

### Linux note

The desktop window needs a GUI backend for pywebview (`pip install pywebview[qt]` or the GTK packages for your
distro). Without one the app opens in your browser instead.
