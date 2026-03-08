from dataclasses import dataclass
from .config import Config
from .data import DataFetcher


@dataclass
class Position:
    ticker: str
    theme: str
    entry_price: float
    current_price: float
    shares: float
    invested: float
    current_value: float
    pnl_dollars: float
    pnl_pct: float
    weight: float  # % of total portfolio


class Portfolio:
    """Computes portfolio state from config + live prices."""

    def __init__(self, config: Config, fetcher: DataFetcher):
        self._config = config
        self._fetcher = fetcher
        self._positions: list[Position] | None = None

    @property
    def cash(self) -> float:
        return self._config.cash

    @property
    def starting_value(self) -> float:
        return self._config.starting_value

    def positions(self) -> list[Position]:
        if self._positions is not None:
            return self._positions

        total_val = self.cash
        raw = []
        for ticker, cfg in self._config.portfolio.items():
            price = self._fetcher.get_latest_price(ticker)
            if price is None:
                continue
            entry = cfg["entry_price"]
            dollars = cfg["dollars"]
            shares = dollars / entry
            val = shares * price
            pnl = val - dollars
            pct = ((price - entry) / entry) * 100
            total_val += val
            raw.append((ticker, cfg["theme"], entry, price, shares, dollars, val, pnl, pct))

        self._positions = []
        for ticker, theme, entry, price, shares, dollars, val, pnl, pct in raw:
            weight = (val / total_val * 100) if total_val > 0 else 0
            self._positions.append(Position(
                ticker=ticker, theme=theme, entry_price=entry,
                current_price=price, shares=shares, invested=dollars,
                current_value=val, pnl_dollars=pnl, pnl_pct=pct, weight=weight,
            ))
        return self._positions

    def total_value(self) -> float:
        return self.cash + sum(p.current_value for p in self.positions())

    def total_invested(self) -> float:
        return self.cash + sum(p.invested for p in self.positions())

    def total_pnl(self) -> float:
        return sum(p.pnl_dollars for p in self.positions())

    def total_return_pct(self) -> float:
        return ((self.total_value() / self.starting_value) - 1) * 100

    def benchmark_returns(self) -> dict[str, float]:
        results = {}
        for bench in self._config.benchmarks:
            df = self._fetcher.fetch(bench, period="ytd")
            if df is not None and len(df) > 1:
                start = df['Close'].iloc[0]
                end = df['Close'].iloc[-1]
                results[bench] = ((end - start) / start) * 100
        return results
