#!/usr/bin/env python3
"""
تطبيق تحليل فرص التداول
Trading Opportunity Analyzer
"""
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich import box

from data_fetcher import DataFetcher
from analyzer import TradingAnalyzer, Signal


console = Console()


def get_signal_color(signal: Signal) -> str:
    """الحصول على لون الإشارة"""
    colors = {
        Signal.STRONG_BUY: "bold green",
        Signal.BUY: "green",
        Signal.NEUTRAL: "yellow",
        Signal.SELL: "red",
        Signal.STRONG_SELL: "bold red"
    }
    return colors.get(signal, "white")


def display_analysis(opportunity):
    """عرض نتائج التحليل"""
    console.print()

    # عنوان
    title = Text(f"تحليل {opportunity.symbol}", style="bold cyan")
    console.print(Panel(title, box=box.DOUBLE))

    # جدول الإشارة الرئيسية
    signal_table = Table(box=box.ROUNDED, show_header=False)
    signal_table.add_column("", style="bold")
    signal_table.add_column("")

    signal_color = get_signal_color(opportunity.signal)
    signal_table.add_row("الإشارة", Text(opportunity.signal.value, style=signal_color))
    signal_table.add_row("درجة الثقة", f"{opportunity.confidence:.1f}%")
    signal_table.add_row("الاتجاه العام", opportunity.trend.value)
    signal_table.add_row("نسبة المخاطرة/العائد", f"1:{opportunity.risk_reward_ratio:.2f}")

    console.print(Panel(signal_table, title="الإشارة", border_style="cyan"))

    # جدول مستويات التداول
    levels_table = Table(box=box.ROUNDED)
    levels_table.add_column("المستوى", style="bold")
    levels_table.add_column("السعر", justify="right")

    if opportunity.signal in [Signal.STRONG_BUY, Signal.BUY]:
        levels_table.add_row("سعر الدخول (شراء)", f"${opportunity.entry_price:.4f}", style="green")
        levels_table.add_row("وقف الخسارة", f"${opportunity.stop_loss:.4f}", style="red")
        levels_table.add_row("الهدف الأول", f"${opportunity.take_profit_1:.4f}", style="cyan")
        levels_table.add_row("الهدف الثاني", f"${opportunity.take_profit_2:.4f}", style="cyan")
        levels_table.add_row("الهدف الثالث", f"${opportunity.take_profit_3:.4f}", style="cyan")
    elif opportunity.signal in [Signal.STRONG_SELL, Signal.SELL]:
        levels_table.add_row("سعر الدخول (بيع)", f"${opportunity.entry_price:.4f}", style="red")
        levels_table.add_row("وقف الخسارة", f"${opportunity.stop_loss:.4f}", style="green")
        levels_table.add_row("الهدف الأول", f"${opportunity.take_profit_1:.4f}", style="cyan")
        levels_table.add_row("الهدف الثاني", f"${opportunity.take_profit_2:.4f}", style="cyan")
        levels_table.add_row("الهدف الثالث", f"${opportunity.take_profit_3:.4f}", style="cyan")
    else:
        levels_table.add_row("السعر الحالي", f"${opportunity.entry_price:.4f}")
        levels_table.add_row("انتظر إشارة أوضح", "-", style="yellow")

    console.print(Panel(levels_table, title="مستويات التداول", border_style="green"))

    # أسباب التوصية
    reasons_text = "\n".join([f"• {reason}" for reason in opportunity.reasons])
    console.print(Panel(reasons_text, title="أسباب التوصية", border_style="magenta"))

    # تحذير
    warning = Text(
        "تحذير: هذا التحليل للأغراض التعليمية فقط. التداول ينطوي على مخاطر عالية. "
        "لا تستثمر أموالاً لا يمكنك تحمل خسارتها.",
        style="bold yellow"
    )
    console.print(Panel(warning, border_style="yellow"))
    console.print()


def analyze_symbol(symbol: str):
    """تحليل رمز معين"""
    console.print(f"\nجاري جلب بيانات [cyan]{symbol}[/cyan]...", end=" ")

    fetcher = DataFetcher()
    data = fetcher.fetch_data(symbol, period="3mo", interval="1d")

    if data is None:
        console.print("[red]فشل![/red]")
        console.print(f"[red]لم يتم العثور على بيانات للرمز: {symbol}[/red]")
        return

    console.print("[green]تم![/green]")
    console.print("جاري التحليل...", end=" ")

    analyzer = TradingAnalyzer(data, symbol)
    opportunity = analyzer.analyze()

    console.print("[green]تم![/green]")
    display_analysis(opportunity)


def analyze_multiple(symbols: list):
    """تحليل عدة رموز"""
    results = []

    for symbol in symbols:
        console.print(f"جاري تحليل [cyan]{symbol}[/cyan]...", end=" ")
        fetcher = DataFetcher()
        data = fetcher.fetch_data(symbol, period="3mo", interval="1d")

        if data is not None:
            analyzer = TradingAnalyzer(data, symbol)
            opportunity = analyzer.analyze()
            results.append(opportunity)
            console.print("[green]تم[/green]")
        else:
            console.print("[red]فشل[/red]")

    # عرض ملخص
    if results:
        console.print()
        summary_table = Table(title="ملخص التحليل", box=box.DOUBLE_EDGE)
        summary_table.add_column("الرمز", style="cyan")
        summary_table.add_column("الإشارة")
        summary_table.add_column("الثقة", justify="right")
        summary_table.add_column("الاتجاه")
        summary_table.add_column("السعر", justify="right")

        for opp in results:
            signal_color = get_signal_color(opp.signal)
            summary_table.add_row(
                opp.symbol,
                Text(opp.signal.value, style=signal_color),
                f"{opp.confidence:.0f}%",
                opp.trend.value,
                f"${opp.entry_price:.2f}"
            )

        console.print(summary_table)
        console.print()


def show_menu():
    """عرض القائمة الرئيسية"""
    console.print()
    console.print(Panel(
        "[bold cyan]محلل فرص التداول[/bold cyan]\n"
        "[dim]Trading Opportunity Analyzer[/dim]",
        box=box.DOUBLE
    ))
    console.print()
    console.print("[1] تحليل رمز واحد")
    console.print("[2] تحليل عدة رموز")
    console.print("[3] تحليل أشهر الأسهم")
    console.print("[4] تحليل العملات الرقمية")
    console.print("[5] تحليل أزواج الفوركس")
    console.print("[0] خروج")
    console.print()


def main():
    """الدالة الرئيسية"""
    # التحقق من وجود وسائط سطر الأوامر
    if len(sys.argv) > 1:
        symbols = sys.argv[1:]
        if len(symbols) == 1:
            analyze_symbol(symbols[0])
        else:
            analyze_multiple(symbols)
        return

    # الوضع التفاعلي
    while True:
        show_menu()
        choice = console.input("[bold]اختر خياراً: [/bold]")

        if choice == "1":
            symbol = console.input("أدخل رمز السهم (مثل AAPL): ").upper().strip()
            if symbol:
                analyze_symbol(symbol)

        elif choice == "2":
            symbols_input = console.input("أدخل الرموز مفصولة بفواصل (مثل AAPL,GOOGL,MSFT): ")
            symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]
            if symbols:
                analyze_multiple(symbols)

        elif choice == "3":
            # أشهر الأسهم
            popular_stocks = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA"]
            analyze_multiple(popular_stocks)

        elif choice == "4":
            # العملات الرقمية
            crypto = ["BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "SOL-USD"]
            analyze_multiple(crypto)

        elif choice == "5":
            # أزواج الفوركس
            forex = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]
            analyze_multiple(forex)

        elif choice == "0":
            console.print("\n[cyan]شكراً لاستخدامك محلل التداول. وداعاً![/cyan]\n")
            break

        else:
            console.print("[red]خيار غير صحيح. حاول مرة أخرى.[/red]")


if __name__ == "__main__":
    main()
