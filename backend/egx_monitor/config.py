"""User settings, stored as JSON in ~/.egx-monitor/config.json so they survive updates."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("EGX_MONITOR_HOME", Path.home() / ".egx-monitor"))
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_WATCHLIST = [
    "COMI",  # Commercial International Bank
    "TMGH",  # Talaat Moustafa Group
    "EAST",  # Eastern Company
    "HRHO",  # EFG Holding
    "ETEL",  # Telecom Egypt
    "SWDY",  # Elsewedy Electric
    "ABUK",  # Abu Qir Fertilizers
    "FWRY",  # Fawry
    "EFIH",  # e-finance
    "ORAS",  # Orascom Construction
]


@dataclass
class Settings:
    watchlist: list[str] = field(default_factory=lambda: list(DEFAULT_WATCHLIST))
    max_watchlist: int = 25
    # "auto" = live data with simulated fallback, "live" = live only, "simulated" = always simulated
    data_mode: str = "auto"
    # Seconds between refreshes while the market is open / closed.
    refresh_open: int = 15
    refresh_closed: int = 300
    theme: str = "dark"

    @classmethod
    def load(cls) -> "Settings":
        if not CONFIG_FILE.exists():
            # First run: write the defaults so there is a file to find and edit.
            settings = cls()
            try:
                settings.save()
            except OSError:
                pass
            return settings
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # Unreadable or hand-edited into invalid JSON: run on defaults but leave the file alone.
            return cls()
        known = {k: v for k, v in raw.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
