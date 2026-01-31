#!/usr/bin/env python3
"""
Market Decision Engine
Capital preservation first.
"""
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from data_fetcher import DataFetcher
from analyzer import DecisionEngine, Decision, Direction


console = Console()

# Primary markets
MARKETS = {
    'gold': 'GC=F',      # Gold Futures
    'xauusd': 'GC=F',
    'bitcoin': 'BTC-USD',
    'btcusd': 'BTC-USD',
    'btc': 'BTC-USD',
    'eurusd': 'EURUSD=X',
    'gbpusd': 'GBPUSD=X',
}


def get_decision_style(decision: Decision) -> str:
    if decision == Decision.EXECUTE:
        return "bold green"
    elif decision == Decision.PREPARE:
        return "bold yellow"
    return "bold red"


def display_analysis(symbol: str, analysis):
    """Display analysis - direct, no hype"""
    console.print()

    # Decision header
    decision_style = get_decision_style(analysis.decision)
    console.print(f"[{decision_style}]{analysis.decision.value}[/]", justify="center")
    console.print()

    # Context table
    ctx = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    ctx.add_column("", style="dim")
    ctx.add_column("")

    ctx.add_row("Symbol", symbol)
    ctx.add_row("Price", f"{analysis.price:.2f}")
    ctx.add_row("Regime", analysis.regime.value)
    ctx.add_row("EMA 20", f"{analysis.ema_20:.2f}")
    ctx.add_row("EMA 50", f"{analysis.ema_50:.2f}")
    ctx.add_row("RSI", f"{analysis.rsi:.1f}")
    ctx.add_row("ATR", f"{analysis.atr:.2f}")

    console.print(Panel(ctx, title="Context", border_style="dim"))

    # Trade plan if EXECUTE
    if analysis.decision == Decision.EXECUTE and analysis.direction:
        plan = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        plan.add_column("", style="dim")
        plan.add_column("")

        dir_style = "green" if analysis.direction == Direction.BUY else "red"
        plan.add_row("Direction", f"[{dir_style}]{analysis.direction.value}[/]")

        if analysis.entry_zone:
            plan.add_row("Entry Zone", f"{analysis.entry_zone[0]:.2f} - {analysis.entry_zone[1]:.2f}")
        if analysis.stop_loss:
            plan.add_row("Stop Loss", f"[red]{analysis.stop_loss:.2f}[/]")
        if analysis.target:
            plan.add_row("Target", f"[green]{analysis.target:.2f}[/]")
        if analysis.risk_reward:
            plan.add_row("Risk:Reward", f"1:{analysis.risk_reward}")
        if analysis.hold_time:
            plan.add_row("Hold Time", analysis.hold_time)

        console.print(Panel(plan, title="Trade Plan", border_style="green"))

    # Reasons
    if analysis.reasons:
        reasons_text = "\n".join([f"+ {r}" for r in analysis.reasons])
        console.print(Panel(reasons_text, title="Why", border_style="green"))

    # Missing conditions
    if analysis.missing_conditions:
        missing_text = "\n".join([f"- {m}" for m in analysis.missing_conditions])
        console.print(Panel(missing_text, title="Missing", border_style="red"))

    # Watch levels
    if analysis.watch_levels:
        watch_text = "\n".join([f"* {w}" for w in analysis.watch_levels])
        console.print(Panel(watch_text, title="Watch", border_style="yellow"))

    # No trade reminder
    if analysis.decision == Decision.WAIT:
        console.print("\n[dim]No trade is a valid trade.[/dim]", justify="center")

    console.print()


def analyze(symbol: str):
    """Run analysis on symbol"""
    # Resolve symbol alias
    resolved = MARKETS.get(symbol.lower(), symbol.upper())

    console.print(f"\n[dim]Fetching {resolved}...[/dim]")

    fetcher = DataFetcher()
    # Get H1 data (using 1h interval, 1 month of data)
    df = fetcher.fetch_data(resolved, period="1mo", interval="1h")

    if df is None or len(df) < 50:
        console.print(f"[red]Insufficient data for {resolved}[/red]")
        return

    engine = DecisionEngine(df, resolved)
    analysis = engine.analyze()

    display_analysis(resolved, analysis)


def main():
    if len(sys.argv) > 1:
        for symbol in sys.argv[1:]:
            analyze(symbol)
    else:
        console.print("\n[bold]Market Decision Engine[/bold]")
        console.print("[dim]Primary: Gold (XAUUSD), Bitcoin (BTCUSD)[/dim]")
        console.print("[dim]Secondary: EURUSD, GBPUSD[/dim]\n")

        console.print("Usage: python main.py <symbol>")
        console.print("Examples:")
        console.print("  python main.py gold")
        console.print("  python main.py btc")
        console.print("  python main.py eurusd")
        console.print()


if __name__ == "__main__":
    main()
