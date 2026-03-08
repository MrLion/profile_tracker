import pandas as pd
from datetime import datetime

from core.portfolio import Portfolio
from strategies.base import Strategy, Signal


class CSVExport:
    """Exports portfolio + strategy signals to a CSV file."""

    def export(self, portfolio: Portfolio, all_signals: dict[str, list[Signal]],
               filename: str | None = None) -> str:
        if filename is None:
            filename = f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

        rows = []
        # Map signals by ticker for quick lookup
        sig_by_ticker: dict[str, dict[str, Signal]] = {}
        for slug, signals in all_signals.items():
            for sig in signals:
                sig_by_ticker.setdefault(sig.ticker, {})[slug] = sig

        for pos in portfolio.positions():
            row = {
                "Ticker": pos.ticker,
                "Theme": pos.theme,
                "Entry": pos.entry_price,
                "Current": round(pos.current_price, 2),
                "Shares": round(pos.shares, 4),
                "Invested": pos.invested,
                "Value": round(pos.current_value, 2),
                "PnL_$": round(pos.pnl_dollars, 2),
                "PnL_%": round(pos.pnl_pct, 2),
                "Weight_%": round(pos.weight, 2),
            }

            # Append each strategy's metrics
            for slug, sig in sig_by_ticker.get(pos.ticker, {}).items():
                row[f"{slug}_stage"] = sig.label
                row[f"{slug}_action"] = sig.action
                for k, v in sig.metrics.items():
                    if isinstance(v, float):
                        row[f"{slug}_{k}"] = round(v, 2)
                    else:
                        row[f"{slug}_{k}"] = v

            rows.append(row)

        pd.DataFrame(rows).to_csv(filename, index=False)
        print(f"\n  📁 Exported to {filename}")
        return filename
