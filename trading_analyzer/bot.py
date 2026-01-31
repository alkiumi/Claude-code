#!/usr/bin/env python3
"""
Telegram Bot - Market Decision Engine
Using pyTelegramBotAPI (telebot)
"""
import os
import telebot
from data_fetcher import DataFetcher
from analyzer import DecisionEngine, Decision, Direction

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

    if analysis.decision == Decision.EXECUTE:
        decision_icon = "🟢"
    elif analysis.decision == Decision.PREPARE:
        decision_icon = "🟡"
    else:
        decision_icon = "🔴"

    dir_icon = ""
    if analysis.direction:
        dir_icon = "📈" if analysis.direction == Direction.BUY else "📉"

    msg = f"""{decision_icon} *{analysis.decision.value}* {dir_icon}

*{symbol}* | {analysis.regime.value}

`Price:   ${analysis.price:,.2f}`
`EMA 20:  ${analysis.ema_20:,.2f}`
`EMA 50:  ${analysis.ema_50:,.2f}`
`RSI:     {analysis.rsi:.1f}`
`ATR:     ${analysis.atr:,.2f}`"""

    if analysis.decision == Decision.EXECUTE and analysis.direction:
        dir_text = "🟢 BUY" if analysis.direction == Direction.BUY else "🔴 SELL"
        msg += f"""

*Trade Plan:*
`Direction:  {dir_text}`
`Entry:      ${analysis.entry_zone[0]:,.2f} - ${analysis.entry_zone[1]:,.2f}`
`Stop Loss:  ${analysis.stop_loss:,.2f}`
`Target:     ${analysis.target:,.2f}`
`R:R:        1:{analysis.risk_reward}`"""

    if analysis.reasons:
        msg += "\n\n✅ *Why:*\n"
        for r in analysis.reasons:
            msg += f"• {r}\n"

    if analysis.missing_conditions:
        msg += "\n❌ *Missing:*\n"
        for m in analysis.missing_conditions:
            msg += f"• {m}\n"

    if analysis.watch_levels:
        msg += "\n👀 *Watch:*\n"
        for w in analysis.watch_levels:
            msg += f"• {w}\n"

    if analysis.decision == Decision.WAIT:
        msg += "\n_No trade is a valid trade._"

    return msg


def analyze_market(symbol: str) -> str:
    """Run analysis"""
    resolved = MARKETS.get(symbol.lower(), symbol.upper())

    fetcher = DataFetcher()
    df = fetcher.fetch_data(resolved, period="1mo", interval="1h")

    if df is None or len(df) < 50:
        return f"❌ No data for {resolved}"

    engine = DecisionEngine(df, resolved)
    analysis = engine.analyze()

    return format_analysis(resolved, analysis)


def run_bot(token: str):
    """Run the bot"""
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['start', 'help'])
    def start(message):
        msg = """🎯 *Market Decision Engine*

Capital preservation first.

*Commands:*
/gold - Gold (XAUUSD)
/btc - Bitcoin (BTC/USD)
/eurusd - EUR/USD
/gbpusd - GBP/USD
/scan - Scan all markets
/a <symbol> - Any symbol

*Decisions:*
🟢 EXECUTE - Clear setup
🟡 PREPARE - Watch for entry
🔴 WAIT - Stay out"""
        bot.reply_to(message, msg, parse_mode='Markdown')

    @bot.message_handler(commands=['gold', 'xauusd'])
    def gold(message):
        bot.reply_to(message, "⏳ Analyzing Gold...")
        result = analyze_market('gold')
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    @bot.message_handler(commands=['btc', 'bitcoin'])
    def btc(message):
        bot.reply_to(message, "⏳ Analyzing Bitcoin...")
        result = analyze_market('btc')
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    @bot.message_handler(commands=['eurusd'])
    def eurusd(message):
        bot.reply_to(message, "⏳ Analyzing EUR/USD...")
        result = analyze_market('eurusd')
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    @bot.message_handler(commands=['gbpusd'])
    def gbpusd(message):
        bot.reply_to(message, "⏳ Analyzing GBP/USD...")
        result = analyze_market('gbpusd')
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    @bot.message_handler(commands=['a', 'analyze'])
    def analyze(message):
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "Usage: /a AAPL")
            return
        symbol = parts[1]
        bot.reply_to(message, f"⏳ Analyzing {symbol.upper()}...")
        result = analyze_market(symbol)
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    @bot.message_handler(commands=['scan'])
    def scan(message):
        bot.reply_to(message, "⏳ Scanning markets...")

        results = []
        for market in ['gold', 'btc', 'eurusd']:
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

                results.append(f"{icon} *{resolved}* {dir_text} | {analysis.decision.value}")

        msg = "📊 *Market Scan*\n\n" + "\n".join(results)
        bot.send_message(message.chat.id, msg, parse_mode='Markdown')

    print("Bot is running...")
    bot.infinity_polling()


if __name__ == "__main__":
    token = os.environ.get('TELEGRAM_BOT_TOKEN')

    if not token:
        print("Set TELEGRAM_BOT_TOKEN environment variable")
        print("export TELEGRAM_BOT_TOKEN='your_token'")
        print("python bot.py")
    else:
        run_bot(token)
