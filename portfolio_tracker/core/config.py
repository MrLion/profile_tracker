import json
import os
import sys
from datetime import datetime


class Config:
    """Loads and manages portfolio.json — single source of truth for portfolio state."""

    def __init__(self, path=None):
        if path is None:
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "portfolio.json")
        self.path = path
        self._data = self._load()

    def _load(self) -> dict:
        if not os.path.exists(self.path):
            print(f"  ❌ Config not found: {self.path}")
            sys.exit(1)
        with open(self.path, "r") as f:
            return json.load(f)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=4)
        print(f"  💾 Saved {self.path}")

    # ── Properties ──

    @property
    def portfolio(self) -> dict:
        return self._data.get("portfolio", {})

    @property
    def cash(self) -> float:
        return self._data.get("cash", 0)

    @cash.setter
    def cash(self, value: float):
        self._data["cash"] = round(value, 2)

    @property
    def starting_value(self) -> float:
        return self._data.get("starting_value", 10000)

    @property
    def watchlist(self) -> list:
        return self._data.get("watchlist", [])

    @property
    def benchmarks(self) -> list:
        return self._data.get("benchmarks", ["SPY", "QQQ", "DIA"])

    @property
    def closed_trades(self) -> list:
        return self._data.get("closed_trades", [])

    # ── Mutations ──

    def add_position(self, ticker: str, entry_price: float, dollars: float, theme: str = "Uncategorized"):
        ticker = ticker.upper()
        self._data["portfolio"][ticker] = {
            "entry_price": entry_price,
            "dollars": dollars,
            "theme": theme,
        }

    def remove_position(self, ticker: str) -> dict | None:
        ticker = ticker.upper()
        return self._data["portfolio"].pop(ticker, None)

    def record_trade(self, ticker: str, action: str, price: float, dollars: float, reason: str = ""):
        if "closed_trades" not in self._data:
            self._data["closed_trades"] = []
        self._data["closed_trades"].append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "ticker": ticker.upper(),
            "action": action,
            "price": price,
            "dollars": round(dollars, 2),
            "reason": reason,
        })

    def add_to_watchlist(self, ticker: str):
        ticker = ticker.upper()
        if ticker not in self._data["watchlist"]:
            self._data["watchlist"].append(ticker)

    def remove_from_watchlist(self, ticker: str):
        ticker = ticker.upper()
        self._data["watchlist"] = [t for t in self._data["watchlist"] if t != ticker]
