"""FastAPI app: JSON API under /api, built TypeScript dashboard served at /."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .brief import build_brief
from .config import Settings
from .service import MarketService

STATIC_DIR = Path(__file__).parent / "static"

settings = Settings.load()
service = MarketService(settings)
app = FastAPI(title="EGX Monitor")
# The Vite dev server (npm run dev) runs on another port.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class WatchlistIn(BaseModel):
    symbols: list[str]


class SettingsIn(BaseModel):
    data_mode: str | None = None
    theme: str | None = None


@app.get("/api/snapshot")
async def snapshot(force: bool = False):
    return await service.snapshot(force=force)


@app.get("/api/chart/{symbol}")
async def chart(symbol: str, range: str = "1D"):
    try:
        return await service.chart(symbol.upper(), range)
    except Exception as exc:
        raise HTTPException(502, f"Could not load chart for {symbol}: {exc}") from exc


@app.get("/api/brief")
async def brief(kind: str = "market"):
    snap = await service.snapshot()
    return {"kind": kind, "text": build_brief(snap, kind), "source": snap["source"]}


@app.put("/api/watchlist")
async def put_watchlist(body: WatchlistIn):
    return {"watchlist": service.set_watchlist(body.symbols)}


@app.get("/api/settings")
async def get_settings():
    return {"data_mode": settings.data_mode, "theme": settings.theme}


@app.patch("/api/settings")
async def patch_settings(body: SettingsIn):
    if body.data_mode in {"auto", "live", "simulated"}:
        settings.data_mode = body.data_mode
        service._snapshot_at = 0
        service._bars_cache.clear()
    if body.theme in {"dark", "light"}:
        settings.theme = body.theme
    settings.save()
    return await get_settings()


if (STATIC_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
else:
    @app.get("/", response_class=HTMLResponse)
    async def not_built():
        return (
            "<body style='background:#0b0d10;color:#ddd;font-family:sans-serif;padding:40px'>"
            "<h2>Dashboard not built yet</h2><p>Run <code>cd frontend &amp;&amp; npm install &amp;&amp; npm run build</code>, "
            "or use the setup script.</p></body>"
        )
