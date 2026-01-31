#!/usr/bin/env python3
"""
Telegram Bot - Market Decision Engine
"""
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from data_fetcher import DataFetcher
from analyzer import DecisionEngine, Decision, Direction

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Markets
MARKETS = {
    'gold': 'GC=F',
    'xauusd': 'GC=F',
    'bitcoin': 'BTC-USD',
    'btcusd': 'BTC-USD',
    'btc': 'BTC-USD',
    'eurusd': 'EURUSD=X',
    'gbpusd': 'GBPUSD=X',
}


def format_analysis(symbol: str, analysis) -> str:
    """Format analysis for Telegram"""

    # Decision emoji
    if analysis.decision == Decision.EXECUTE:
        decision_icon = "🟢"
    elif analysis.decision == Decision.PREPARE:
        decision_icon = "🟡"
    else:
        decision_icon = "🔴"

    # Direction emoji
    dir_icon = ""
    if analysis.direction:
        dir_icon = "📈" if analysis.direction == Direction.BUY else "📉"

    msg = f"""
{decision_icon} **{analysis.decision.value}** {dir_icon}

**{symbol}** | {analysis.regime.value}

```
Price:   ${analysis.price:,.2f}
EMA 20:  ${analysis.ema_20:,.2f}
EMA 50:  ${analysis.ema_50:,.2f}
RSI:     {analysis.rsi:.1f}
ATR:     ${analysis.atr:,.2f}
```"""

    # Trade plan
    if analysis.decision == Decision.EXECUTE and analysis.direction:
        dir_text = "🟢 BUY" if analysis.direction == Direction.BUY else "🔴 SELL"
        msg += f"""

**Trade Plan:**
```
Direction:  {dir_text}
Entry:      ${analysis.entry_zone[0]:,.2f} - ${analysis.entry_zone[1]:,.2f}
Stop Loss:  ${analysis.stop_loss:,.2f}
Target:     ${analysis.target:,.2f}
R:R:        1:{analysis.risk_reward}
Hold:       {analysis.hold_time}
```"""

    # Reasons
    if analysis.reasons:
        msg += "\n\n✅ **Why:**\n"
        for r in analysis.reasons:
            msg += f"• {r}\n"

    # Missing
    if analysis.missing_conditions:
        msg += "\n❌ **Missing:**\n"
        for m in analysis.missing_conditions:
            msg += f"• {m}\n"

    # Watch
    if analysis.watch_levels:
        msg += "\n👀 **Watch:**\n"
        for w in analysis.watch_levels:
            msg += f"• {w}\n"

    # No trade reminder
    if analysis.decision == Decision.WAIT:
        msg += "\n_No trade is a valid trade._"

    return msg


async def analyze_market(symbol: str) -> str:
    """Run analysis and return formatted message"""
    resolved = MARKETS.get(symbol.lower(), symbol.upper())

    fetcher = DataFetcher()
    df = fetcher.fetch_data(resolved, period="1mo", interval="1h")

    if df is None or len(df) < 50:
        return f"❌ No data for {resolved}"

    engine = DecisionEngine(df, resolved)
    analysis = engine.analyze()

    return format_analysis(resolved, analysis)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    msg = """
🎯 **Market Decision Engine**

Capital preservation first.

**Commands:**
/gold - Gold (XAUUSD)
/btc - Bitcoin
/eurusd - EUR/USD
/gbpusd - GBP/USD
/analyze <symbol> - Any symbol

**Decisions:**
🟢 EXECUTE - Clear setup
🟡 PREPARE - Watch for entry
🔴 WAIT - Stay out
"""
    await update.message.reply_text(msg, parse_mode='Markdown')


async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze Gold"""
    await update.message.reply_text("⏳ Analyzing Gold...")
    msg = await analyze_market('gold')
    await update.message.reply_text(msg, parse_mode='Markdown')


async def btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze Bitcoin"""
    await update.message.reply_text("⏳ Analyzing Bitcoin...")
    msg = await analyze_market('btc')
    await update.message.reply_text(msg, parse_mode='Markdown')


async def eurusd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze EUR/USD"""
    await update.message.reply_text("⏳ Analyzing EUR/USD...")
    msg = await analyze_market('eurusd')
    await update.message.reply_text(msg, parse_mode='Markdown')


async def gbpusd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze GBP/USD"""
    await update.message.reply_text("⏳ Analyzing GBP/USD...")
    msg = await analyze_market('gbpusd')
    await update.message.reply_text(msg, parse_mode='Markdown')


async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analyze any symbol"""
    if not context.args:
        await update.message.reply_text("Usage: /analyze AAPL")
        return

    symbol = context.args[0]
    await update.message.reply_text(f"⏳ Analyzing {symbol.upper()}...")
    msg = await analyze_market(symbol)
    await update.message.reply_text(msg, parse_mode='Markdown')


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan all primary markets"""
    await update.message.reply_text("⏳ Scanning markets...")

    markets = ['gold', 'btc', 'eurusd']
    results = []

    for market in markets:
        resolved = MARKETS.get(market)
        fetcher = DataFetcher()
        df = fetcher.fetch_data(resolved, period="1mo", interval="1h")

        if df is not None and len(df) >= 50:
            engine = DecisionEngine(df, resolved)
            analysis = engine.analyze()

            icon = "🟢" if analysis.decision == Decision.EXECUTE else "🟡" if analysis.decision == Decision.PREPARE else "🔴"
            dir_text = ""
            if analysis.direction:
                dir_text = "↑" if analysis.direction == Direction.BUY else "↓"

            results.append(f"{icon} **{resolved}** {dir_text} | {analysis.decision.value} | {analysis.regime.value}")

    msg = "📊 **Market Scan**\n\n" + "\n".join(results)
    await update.message.reply_text(msg, parse_mode='Markdown')


def main():
    """Run bot"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')

    if not token:
        print("=" * 50)
        print("TELEGRAM BOT SETUP")
        print("=" * 50)
        print()
        print("1. Open Telegram and search for @BotFather")
        print("2. Send /newbot")
        print("3. Choose a name for your bot")
        print("4. Copy the token")
        print("5. Run:")
        print()
        print("   export TELEGRAM_BOT_TOKEN='your_token_here'")
        print("   python bot.py")
        print()
        print("=" * 50)
        return

    # Build app
    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gold", gold))
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("eurusd", eurusd))
    app.add_handler(CommandHandler("gbpusd", gbpusd))
    app.add_handler(CommandHandler("analyze", analyze))
    app.add_handler(CommandHandler("scan", scan))

    # Run
    print("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
