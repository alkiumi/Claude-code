#!/usr/bin/env python3
"""
Telegram Bot - Market Decision Engine
Arabic Interface
"""
import os
import telebot
from data_fetcher import DataFetcher
from analyzer import DecisionEngine, Decision, Direction

# Markets
MARKETS = {
    'gold': 'GC=F',
    'xauusd': 'GC=F',
    'ذهب': 'GC=F',
    'bitcoin': 'BTC-USD',
    'btcusd': 'BTC-USD',
    'btc': 'BTC-USD',
    'بتكوين': 'BTC-USD',
    'eurusd': 'EURUSD=X',
    'gbpusd': 'GBPUSD=X',
}

# Arabic translations
DECISION_AR = {
    Decision.EXECUTE: "تنفيذ",
    Decision.PREPARE: "استعد",
    Decision.WAIT: "انتظر",
}

REGIME_AR = {
    "Uptrend": "صاعد",
    "Downtrend": "هابط",
    "Range": "عرضي",
    "Correction": "تصحيح",
    "Unclear": "غير واضح",
}


def format_analysis(symbol: str, analysis) -> str:
    """Format analysis in Arabic"""

    if analysis.decision == Decision.EXECUTE:
        decision_icon = "🟢"
    elif analysis.decision == Decision.PREPARE:
        decision_icon = "🟡"
    else:
        decision_icon = "🔴"

    dir_icon = ""
    if analysis.direction:
        dir_icon = "📈" if analysis.direction == Direction.BUY else "📉"

    decision_ar = DECISION_AR.get(analysis.decision, analysis.decision.value)
    regime_ar = REGIME_AR.get(analysis.regime.value, analysis.regime.value)

    msg = f"""{decision_icon} *{decision_ar}* {dir_icon}

*{symbol}* | {regime_ar}

`السعر:    ${analysis.price:,.2f}`
`EMA 20:  ${analysis.ema_20:,.2f}`
`EMA 50:  ${analysis.ema_50:,.2f}`
`RSI:     {analysis.rsi:.1f}`
`ATR:     ${analysis.atr:,.2f}`"""

    if analysis.decision == Decision.EXECUTE and analysis.direction:
        dir_text = "🟢 شراء" if analysis.direction == Direction.BUY else "🔴 بيع"
        msg += f"""

*خطة الصفقة:*
`الاتجاه:     {dir_text}`
`الدخول:     ${analysis.entry_zone[0]:,.2f} - ${analysis.entry_zone[1]:,.2f}`
`وقف الخسارة: ${analysis.stop_loss:,.2f}`
`الهدف:      ${analysis.target:,.2f}`
`المخاطرة:   1:{analysis.risk_reward}`"""

    if analysis.reasons:
        msg += "\n\n✅ *الأسباب:*\n"
        for r in analysis.reasons:
            # Translate common reasons
            r_ar = translate_reason(r)
            msg += f"• {r_ar}\n"

    if analysis.missing_conditions:
        msg += "\n❌ *ينقص:*\n"
        for m in analysis.missing_conditions:
            m_ar = translate_reason(m)
            msg += f"• {m_ar}\n"

    if analysis.watch_levels:
        msg += "\n👀 *راقب:*\n"
        for w in analysis.watch_levels:
            w_ar = translate_reason(w)
            msg += f"• {w_ar}\n"

    if analysis.decision == Decision.WAIT:
        msg += "\n_عدم التداول قرار صحيح._"

    return msg


def translate_reason(text: str) -> str:
    """Translate common reasons to Arabic"""
    translations = {
        "Clear Uptrend regime": "اتجاه صاعد واضح",
        "Clear Downtrend regime": "اتجاه هابط واضح",
        "Price in healthy position above EMA 20": "السعر في موقع صحي فوق EMA 20",
        "Price in healthy position below EMA 20": "السعر في موقع صحي تحت EMA 20",
        "EMA 20 showing strong slope": "EMA 20 يظهر ميل قوي",
        "RSI momentum rising": "زخم RSI يرتفع",
        "RSI momentum falling": "زخم RSI يهبط",
        "Price rejection at key level": "رفض السعر عند مستوى مهم",
        "Price accepting current level": "السعر يقبل المستوى الحالي",
        "Price compressing - breakout imminent": "السعر ينضغط - اختراق وشيك",
        "Market in correction phase": "السوق في مرحلة تصحيح",
        "No clear trend - range bound": "لا يوجد اتجاه واضح - سوق عرضي",
        "Regime unclear - no trade": "الوضع غير واضح - لا تداول",
        "EMA 20 slope weak - momentum lacking": "ميل EMA 20 ضعيف - الزخم ناقص",
        "Price overextended from EMA 20": "السعر بعيد جداً عن EMA 20",
    }

    for eng, ar in translations.items():
        if eng in text:
            return text.replace(eng, ar)

    # Translate RSI mentions
    if "RSI (" in text and ") in bullish zone" in text:
        return text.replace(") in bullish zone", ") في المنطقة الصاعدة")
    if "RSI (" in text and ") in bearish zone" in text:
        return text.replace(") in bearish zone", ") في المنطقة الهابطة")
    if "RSI (" in text and ") overheated" in text:
        return text.replace(") overheated", ") محموم - تشبع شرائي")
    if "RSI (" in text and ") oversold" in text:
        return text.replace(") oversold", ") تشبع بيعي")

    # Translate watch levels
    if "Wait for pullback to" in text:
        return text.replace("Wait for pullback to", "انتظر تراجع إلى")
    if "watch for reclaim at" in text:
        return text.replace("Price below EMA 20 - watch for reclaim at", "السعر تحت EMA 20 - راقب استعادة")
    if "watch for rejection at" in text:
        return text.replace("Price above EMA 20 - watch for rejection at", "السعر فوق EMA 20 - راقب رفض عند")

    return text


def analyze_market(symbol: str) -> str:
    """Run analysis"""
    resolved = MARKETS.get(symbol.lower(), symbol.upper())

    fetcher = DataFetcher()
    df = fetcher.fetch_data(resolved, period="1mo", interval="1h")

    if df is None or len(df) < 50:
        return f"❌ لا توجد بيانات لـ {resolved}"

    engine = DecisionEngine(df, resolved)
    analysis = engine.analyze()

    return format_analysis(resolved, analysis)


def run_bot(token: str):
    """Run the bot"""
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['start', 'help', 'ابدأ'])
    def start(message):
        msg = """🎯 *محرك قرارات السوق*

الحفاظ على رأس المال أولاً.

*الأوامر:*
/gold - الذهب
/btc - البيتكوين
/eurusd - يورو/دولار
/scan - فحص الأسواق

*القرارات:*
🟢 تنفيذ - فرصة واضحة
🟡 استعد - راقب للدخول
🔴 انتظر - ابتعد

_عدم التداول قرار صحيح._"""
        bot.reply_to(message, msg, parse_mode='Markdown')

    @bot.message_handler(commands=['gold', 'xauusd', 'ذهب'])
    def gold(message):
        bot.reply_to(message, "⏳ جاري تحليل الذهب...")
        result = analyze_market('gold')
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    @bot.message_handler(commands=['btc', 'bitcoin', 'بتكوين'])
    def btc(message):
        bot.reply_to(message, "⏳ جاري تحليل البيتكوين...")
        result = analyze_market('btc')
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    @bot.message_handler(commands=['eurusd'])
    def eurusd(message):
        bot.reply_to(message, "⏳ جاري تحليل EUR/USD...")
        result = analyze_market('eurusd')
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    @bot.message_handler(commands=['gbpusd'])
    def gbpusd(message):
        bot.reply_to(message, "⏳ جاري تحليل GBP/USD...")
        result = analyze_market('gbpusd')
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    @bot.message_handler(commands=['a', 'analyze', 'حلل'])
    def analyze(message):
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "الاستخدام: /a AAPL")
            return
        symbol = parts[1]
        bot.reply_to(message, f"⏳ جاري تحليل {symbol.upper()}...")
        result = analyze_market(symbol)
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    @bot.message_handler(commands=['scan', 'فحص'])
    def scan(message):
        bot.reply_to(message, "⏳ جاري فحص الأسواق...")

        results = []
        for market, name in [('gold', 'الذهب'), ('btc', 'البيتكوين'), ('eurusd', 'EUR/USD')]:
            resolved = MARKETS.get(market)
            fetcher = DataFetcher()
            df = fetcher.fetch_data(resolved, period="1mo", interval="1h")

            if df is not None and len(df) >= 50:
                engine = DecisionEngine(df, resolved)
                analysis = engine.analyze()

                icon = "🟢" if analysis.decision == Decision.EXECUTE else "🟡" if analysis.decision == Decision.PREPARE else "🔴"
                decision_ar = DECISION_AR.get(analysis.decision, analysis.decision.value)

                dir_text = ""
                if analysis.direction:
                    dir_text = "↑ شراء" if analysis.direction == Direction.BUY else "↓ بيع"

                results.append(f"{icon} *{name}* {dir_text} | {decision_ar}")

        msg = "📊 *فحص الأسواق*\n\n" + "\n".join(results)
        bot.send_message(message.chat.id, msg, parse_mode='Markdown')

    print("Bot is running...")
    bot.infinity_polling()


if __name__ == "__main__":
    token = os.environ.get('TELEGRAM_BOT_TOKEN')

    if not token:
        print("Set TELEGRAM_BOT_TOKEN environment variable")
    else:
        run_bot(token)
