import pandas as pd

from strategies.base import Strategy, Signal
from core.portfolio import Position
from core import indicators as ind


class RelativeStrengthStrategy(Strategy):
    """
    Relative Strength vs Benchmark.
    Compares a stock's return over multiple timeframes against SPY.
    RS > 100 = outperforming, RS < 100 = underperforming.
    """

    def __init__(self, benchmark: str = "SPY"):
        self._benchmark = benchmark
        self._bench_df: pd.DataFrame | None = None

    @property
    def name(self) -> str:
        return f"Relative Strength vs {self._benchmark}"

    @property
    def slug(self) -> str:
        return "rs"

    def set_benchmark_data(self, df: pd.DataFrame):
        self._bench_df = df

    def analyze(self, ticker: str, df: pd.DataFrame,
                position: Position | None = None) -> Signal:
        if self._bench_df is None:
            return Signal(ticker=ticker, action="—", severity="gray",
                          label="N/A", detail="No benchmark data",
                          metrics={})

        rs_1m = self._rs_score(df, self._bench_df, 21)
        rs_3m = self._rs_score(df, self._bench_df, 63)
        rs_6m = self._rs_score(df, self._bench_df, 126)
        rs_12m = self._rs_score(df, self._bench_df, 252)

        # Composite: weighted average
        scores = [s for s in [rs_1m, rs_3m, rs_6m, rs_12m] if s is not None]
        weights = [0.15, 0.25, 0.30, 0.30]
        valid = [(s, w) for s, w in zip([rs_1m, rs_3m, rs_6m, rs_12m], weights) if s is not None]
        if valid:
            total_w = sum(w for _, w in valid)
            composite = sum(s * w for s, w in valid) / total_w
        else:
            composite = None

        if composite is None:
            action, severity = "—", "gray"
            label = "N/A"
        elif composite >= 110:
            action, severity = "🟢 LEADER", "green"
            label = f"RS {composite:.0f}"
        elif composite >= 90:
            action, severity = "🟡 NEUTRAL", "yellow"
            label = f"RS {composite:.0f}"
        else:
            action, severity = "🔴 LAGGARD", "red"
            label = f"RS {composite:.0f}"

        detail = f"{'Outperforming' if (composite or 0) >= 100 else 'Underperforming'} {self._benchmark}"

        return Signal(
            ticker=ticker,
            action=action,
            severity=severity,
            label=label,
            detail=detail,
            metrics={
                "rs_1m": rs_1m,
                "rs_3m": rs_3m,
                "rs_6m": rs_6m,
                "rs_12m": rs_12m,
                "rs_composite": composite,
            },
        )

    def scan_watchlist(self, ticker: str, df: pd.DataFrame) -> Signal | None:
        signal = self.analyze(ticker, df)
        if signal.metrics.get("rs_composite") and signal.metrics["rs_composite"] >= 100:
            return signal
        return None

    def columns(self) -> list[str]:
        return ["RS 1m", "RS 3m", "RS 6m", "RS 12m", "RS Comp", "RS Rating"]

    def row(self, signal: Signal) -> list[str]:
        m = signal.metrics

        def fmt(val):
            return f"{val:.0f}" if val is not None else "N/A"

        return [
            fmt(m.get("rs_1m")),
            fmt(m.get("rs_3m")),
            fmt(m.get("rs_6m")),
            fmt(m.get("rs_12m")),
            fmt(m.get("rs_composite")),
            signal.action,
        ]

    def _rs_score(self, stock_df: pd.DataFrame, bench_df: pd.DataFrame,
                  period: int) -> float | None:
        stock_roc = ind.rate_of_change(stock_df, period)
        bench_roc = ind.rate_of_change(bench_df, period)
        if stock_roc is None or bench_roc is None:
            return None
        if bench_roc == 0:
            return 100.0
        # Normalize: 100 = matching benchmark
        return 100 + (stock_roc - bench_roc)
