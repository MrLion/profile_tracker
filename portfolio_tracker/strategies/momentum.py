import pandas as pd

from strategies.base import Strategy, Signal
from core.portfolio import Position
from core import indicators as ind


class MomentumStrategy(Strategy):
    """
    Momentum Score.
    Composite of Rate of Change over multiple timeframes plus RSI.
    High score = strong momentum, low score = weak/negative momentum.
    """

    @property
    def name(self) -> str:
        return "Momentum Score"

    @property
    def slug(self) -> str:
        return "momentum"

    def analyze(self, ticker: str, df: pd.DataFrame,
                position: Position | None = None) -> Signal:
        roc_20 = ind.rate_of_change(df, 20)
        roc_60 = ind.rate_of_change(df, 60)
        roc_125 = ind.rate_of_change(df, 125)
        current_rsi = ind.rsi_latest(df, 14)

        # Composite momentum score (0-100 scale)
        components = []
        weights = []

        if roc_20 is not None:
            components.append(self._normalize_roc(roc_20))
            weights.append(0.25)
        if roc_60 is not None:
            components.append(self._normalize_roc(roc_60))
            weights.append(0.35)
        if roc_125 is not None:
            components.append(self._normalize_roc(roc_125))
            weights.append(0.40)

        if components:
            total_w = sum(weights)
            score = sum(c * w for c, w in zip(components, weights)) / total_w
        else:
            score = None

        # Momentum accelerating = short-term ROC stronger than medium-term
        accelerating = (roc_20 is not None and roc_60 is not None and roc_20 > roc_60)

        has_position = position is not None

        if score is None:
            action, severity = "—", "gray"
        elif score >= 70:
            if has_position:
                action, severity = "🟢 HOLD", "green"
            elif accelerating and current_rsi and current_rsi < 70:
                action, severity = "🟢 BUY", "green"
            else:
                action, severity = "🟢 STRONG", "green"
        elif score >= 55:
            if not has_position and accelerating:
                action, severity = "⚪ WATCH", "blue"
            elif has_position:
                action, severity = "🟢 HOLD", "green"
            else:
                action, severity = "🟡 MODERATE", "yellow"
        elif score >= 45:
            if has_position:
                action, severity = "🟡 CAUTION", "yellow"
            elif accelerating:
                action, severity = "⚪ WATCH", "blue"
            else:
                action, severity = "🟡 MODERATE", "yellow"
        elif score >= 25:
            action, severity = "🟠 WEAK", "orange"
        else:
            action, severity = "🔴 NEGATIVE", "red"

        label = f"Mom {score:.0f}" if score is not None else "N/A"
        detail = self._build_detail(roc_20, roc_60, roc_125, current_rsi, accelerating)

        return Signal(
            ticker=ticker,
            action=action,
            severity=severity,
            label=label,
            detail=detail,
            metrics={
                "roc_20d": roc_20,
                "roc_60d": roc_60,
                "roc_125d": roc_125,
                "rsi_14": current_rsi,
                "momentum_score": score,
                "accelerating": accelerating,
            },
        )

    def scan_watchlist(self, ticker: str, df: pd.DataFrame) -> Signal | None:
        signal = self.analyze(ticker, df)
        if "BUY" in signal.action or "WATCH" in signal.action:
            return signal
        if signal.metrics.get("momentum_score") and signal.metrics["momentum_score"] >= 60:
            return signal
        return None

    def columns(self) -> list[str]:
        return ["ROC 20d", "ROC 60d", "ROC 125d", "RSI(14)", "Mom Score", "Rating"]

    def row(self, signal: Signal) -> list[str]:
        m = signal.metrics

        def fmt_roc(val):
            return f"{val:+.1f}%" if val is not None else "N/A"

        def fmt_rsi(val):
            if val is None:
                return "N/A"
            tag = ""
            if val > 70:
                tag = " OB"
            elif val < 30:
                tag = " OS"
            return f"{val:.0f}{tag}"

        return [
            fmt_roc(m.get("roc_20d")),
            fmt_roc(m.get("roc_60d")),
            fmt_roc(m.get("roc_125d")),
            fmt_rsi(m.get("rsi_14")),
            f"{m['momentum_score']:.0f}" if m.get("momentum_score") is not None else "N/A",
            signal.action,
        ]

    def _normalize_roc(self, roc: float) -> float:
        """Map ROC to 0-100 scale. 0% ROC = 50, clamped at 0 and 100."""
        normalized = 50 + (roc * 1.5)
        return max(0, min(100, normalized))

    def _build_detail(self, roc_20, roc_60, roc_125, rsi, accelerating=False) -> str:
        parts = []
        if roc_20 is not None:
            parts.append(f"20d: {roc_20:+.1f}%")
        if roc_60 is not None:
            parts.append(f"60d: {roc_60:+.1f}%")
        if rsi is not None:
            if rsi > 70:
                parts.append(f"RSI {rsi:.0f} (overbought)")
            elif rsi < 30:
                parts.append(f"RSI {rsi:.0f} (oversold)")
        if accelerating:
            parts.append("⚡ accelerating")
        return " | ".join(parts) if parts else "Insufficient data"
