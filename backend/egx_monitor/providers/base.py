"""Interface every data source implements. Add a new provider (e.g. a paid broker feed) by subclassing."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import Bar, Quote

INDEX_SYMBOLS = {
    "EGX30": "EGX 30",
    "EGX30CAPPED": "EGX 30 Capped",
    "EGX70EWI": "EGX 70 EWI",
    "EGX100EWI": "EGX 100 EWI",
}
FX_SYMBOLS = {"USDEGP": "USD/EGP", "EUREGP": "EUR/EGP", "GBPEGP": "GBP/EGP"}

# Chart ranges -> (bar interval understood by TradingView, number of bars)
RANGES = {
    "1D": ("5", 80),
    "1W": ("30", 60),
    "1M": ("D", 23),
    "6M": ("D", 130),
    "1Y": ("D", 255),
}


class Provider(ABC):
    name: str = "base"
    live: bool = False

    @abstractmethod
    async def scan_market(self) -> list[Quote]:
        """Every listed stock with its latest quote."""

    @abstractmethod
    async def indices(self) -> list[Quote]: ...

    @abstractmethod
    async def fx(self) -> list[Quote]: ...

    @abstractmethod
    async def bars(self, symbol: str, range_: str) -> list[Bar]: ...
