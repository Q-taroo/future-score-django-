"""Market data Adapter (spec §19) — FX rates, index levels, commodity
prices. MVP ships a Mock implementation; a real vendor plugs in behind
this same interface later."""

import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

BASE_PRICES = {
    "USDJPY": 148.5,
    "EURJPY": 160.2,
    "NIKKEI225": 39500,
    "SP500": 5450,
    "GOLD": 2380,
    "WTI": 78.5,
}


@dataclass(frozen=True)
class MarketQuote:
    symbol: str
    price: float
    change_percent: float


class MarketDataProvider(ABC):
    @abstractmethod
    def get_quote(self, symbol: str) -> MarketQuote: ...


class MockMarketDataProvider(MarketDataProvider):
    def get_quote(self, symbol: str) -> MarketQuote:
        base = BASE_PRICES.get(symbol, 100)
        drift = math.sin(time.time() / 1_000_000 + len(symbol)) * 0.015
        return MarketQuote(symbol=symbol, price=round(base * (1 + drift), 2), change_percent=round(drift * 100, 2))
