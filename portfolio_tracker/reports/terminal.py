from tabulate import tabulate

from core.portfolio import Portfolio
from strategies.base import Strategy, Signal


class TerminalReport:
    """Pretty-prints portfolio data and strategy signals to the terminal."""

    def print_header(self, strategies: list[Strategy]):
        names = ", ".join(s.name for s in strategies)
        print(f"\n  Strategies: {names}")

    def print_pnl(self, portfolio: Portfolio):
        print("\n" + "─" * 72)
        print("  💰 PORTFOLIO P/L")
        print("─" * 72)

        rows = []
        for p in portfolio.positions():
            rows.append([
                p.ticker, p.theme,
                f"${p.entry_price:.2f}", f"${p.current_price:.2f}",
                f"${p.invested:,.0f}", f"${p.current_value:,.0f}",
                f"${p.pnl_dollars:+,.0f}", f"{p.pnl_pct:+.1f}%",
                f"{p.weight:.1f}%",
            ])

        rows.append([
            "CASH", "—", "—", "—",
            f"${portfolio.cash:,.0f}", f"${portfolio.cash:,.0f}",
            "$0", "—",
            f"{(portfolio.cash / portfolio.total_value() * 100):.1f}%" if portfolio.total_value() > 0 else "—",
        ])
        rows.append(["─" * 6, "─" * 16, "─" * 8, "─" * 8, "─" * 8, "─" * 8, "─" * 8, "─" * 8, "─" * 6])
        rows.append([
            "TOTAL", "", "", "",
            f"${portfolio.starting_value:,.0f}",
            f"${portfolio.total_value():,.0f}",
            f"${portfolio.total_pnl():+,.0f}",
            f"{portfolio.total_return_pct():+.2f}%",
            "100%",
        ])

        headers = ["Ticker", "Theme", "Entry", "Current", "Invested",
                    "Value", "P/L $", "P/L %", "Weight"]
        print(tabulate(rows, headers=headers, tablefmt="simple", stralign="right"))

    def print_benchmarks(self, portfolio: Portfolio):
        print("\n" + "─" * 72)
        print("  📈 BENCHMARK COMPARISON (YTD)")
        print("─" * 72)

        bench = portfolio.benchmark_returns()
        for name, ret in bench.items():
            print(f"    {name:5s}: {ret:+.2f}%")
        print(f"    {'PORT':5s}: {portfolio.total_return_pct():+.2f}%")

        # Alpha
        if "SPY" in bench:
            alpha = portfolio.total_return_pct() - bench["SPY"]
            print(f"    {'ALPHA':5s}: {alpha:+.2f}% vs SPY")

    def print_strategy(self, strategy: Strategy, signals: list[Signal]):
        print("\n" + "─" * 72)
        print(f"  🔍 {strategy.name.upper()}")
        print("─" * 72)

        cols = ["Ticker"] + strategy.columns()
        rows = []
        for sig in signals:
            rows.append([sig.ticker] + strategy.row(sig))

        print(tabulate(rows, headers=cols, tablefmt="simple", stralign="right"))

    def print_alerts(self, all_signals: dict[str, list[Signal]]):
        print("\n" + "─" * 72)
        print("  ⚡ ALERTS")
        print("─" * 72)

        found = False
        for slug, signals in all_signals.items():
            for sig in signals:
                if sig.severity in ("red", "orange"):
                    icon = "🔴" if sig.severity == "red" else "🟠"
                    print(f"    {icon} [{slug}] {sig.ticker}: {sig.label} — {sig.action} — {sig.detail}")
                    found = True
                elif sig.severity == "yellow":
                    print(f"    🟡 [{slug}] {sig.ticker}: {sig.label} — {sig.action} — {sig.detail}")
                    found = True

        if not found:
            print("    ✅ No alerts — all positions healthy")

    def print_watchlist(self, strategy: Strategy, signals: list[Signal]):
        if not signals:
            print(f"\n  👀 [{strategy.slug}] No watchlist candidates found.")
            return

        print(f"\n  👀 [{strategy.slug}] WATCHLIST — {strategy.name}")
        cols = ["Ticker"] + strategy.columns()
        rows = [[sig.ticker] + strategy.row(sig) for sig in signals]
        print(tabulate(rows, headers=cols, tablefmt="simple", stralign="right"))
