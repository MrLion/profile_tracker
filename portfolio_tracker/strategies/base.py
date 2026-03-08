from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import pandas as pd

from core.portfolio import Position


@dataclass
class Signal:
    """Output of a strategy's analysis on a single ticker."""
    ticker: str
    action: str       # HOLD, SELL, CAUTION, BUY, TIGHT_STOP
    severity: str     # green, yellow, orange, red
    label: str        # e.g. "Stage 2A ⬆️"
    detail: str       # e.g. "Strong uptrend — above all MAs"
    metrics: dict = field(default_factory=dict)  # strategy-specific numbers


class Strategy(ABC):
    """Abstract base class for all portfolio analysis strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @property
    @abstractmethod
    def slug(self) -> str:
        """Short ID used in CLI and config."""

    @abstractmethod
    def analyze(self, ticker: str, df: pd.DataFrame,
                position: Position | None = None) -> Signal:
        """Run analysis on a single ticker."""

    def analyze_many(self, data: dict[str, pd.DataFrame],
                     positions: list[Position]) -> list[Signal]:
        pos_map = {p.ticker: p for p in positions}
        signals = []
        for ticker, df in data.items():
            sig = self.analyze(ticker, df, pos_map.get(ticker))
            signals.append(sig)
        return signals

    @abstractmethod
    def scan_watchlist(self, ticker: str, df: pd.DataFrame) -> Signal | None:
        """Evaluate a watchlist ticker. Return Signal if interesting, None to skip."""

    @abstractmethod
    def columns(self) -> list[str]:
        """Column headers this strategy adds to the report table."""

    @abstractmethod
    def row(self, signal: Signal) -> list[str]:
        """Format a Signal into table cells matching self.columns()."""
