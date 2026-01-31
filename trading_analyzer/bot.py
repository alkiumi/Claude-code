#!/usr/bin/env python3
"""
Telegram Bot - Market Decision Engine
Six Mandatory Decision Stages
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

DECISION_AR = {
    Decision.EXECUTE: "تنفيذ",
    Decision.PREPARE: "استعد",
    Decision.WAIT: "انتظر",
}


def format_stage(num: int, name: str, result) -> str:
    """Format a single stage"""
    icon = "✅" if result.passed else "❌"
    text = f"*المرحلة {num} - {name}*\n"
    text += f"{icon} {result.summary}\n"
    for detail in result.details:
        text += f"  • {detail}\n"
    return text


def format_analysis(symbol: str, analysis) -> str:
    """Format complete 6-stage analysis"""

    # Decision header
    if analysis.decision == Decision.EXECUTE:
        decision_icon = "🟢"
    elif analysis.decision == Decision.PREPARE:
        decision_icon = "🟡"
    else:
        decision_icon = "🔴"

    decision_ar = DECISION_AR.get(analysis.decision, analysis.decision.value)

    msg = f"{decision_icon} *{decision_ar}*\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"*{symbol}* | ${analysis.price:,.2f}\n\n"

    # Stage 1: Context
    msg += format_stage(1, "السياق", analysis.stage1_context)
    msg += "\n"

    # Stage 2: Location
    msg += format_stage(2, "الموقع", analysis.stage2_location)
    msg += "\n"

    # Stage 3: Momentum
    msg += format_stage(3, "الزخم", analysis.stage3_momentum)
    msg += "\n"

    # Stage 4: Behavior
    msg += format_stage(4, "السلوك", analysis.stage4_behavior)
    msg += "\n"

    # Stage 5: Technical
    msg += format_stage(5, "المستويات", analysis.stage5_technical)
    msg += "\n"

    # Stage 6: Risk
    msg += format_stage(6, "المخاطرة", analysis.stage6_risk)

    # Trade Plan if EXECUTE
    if analysis.decision == Decision.EXECUTE and analysis.direction:
        msg += "\n━━━━━━━━━━━━━━━━━━━━\n"
        msg += "*خطة الصفقة:*\n"
        dir_icon = "🟢" if analysis.direction == Direction.BUY else "🔴"
        msg += f"`الاتجاه:      {dir_icon} {analysis.direction.value}`\n"
        msg += f"`الدخول:      ${analysis.entry_zone[0]:,.2f} - ${analysis.entry_zone[1]:,.2f}`\n"
        msg += f"`وقف الخسارة: ${analysis.stop_loss:,.2f}`\n"
        msg += f"`الهدف:       ${analysis.target:,.2f}`\n"
        msg += f"`المخاطرة:    1:{analysis.risk_reward}`\n"
        msg += f"`المدة:       {analysis.hold_time}`\n"

    # Footer
    msg += "\n━━━━━━━━━━━━━━━━━━━━\n"
    if analysis.decision == Decision.WAIT:
        msg += "_عدم التداول قرار صحيح._"
    elif analysis.decision == Decision.PREPARE:
        msg += "_راقب وانتظر اكتمال الشروط._"
    else:
        msg += "_الحفاظ على رأس المال أولاً._"

    return msg


def analyze_market(symbol: str) -> str:
    """Run 6-stage analysis"""
    resolved = MARKETS.get(symbol.lower(), symbol.upper())

    fetcher = DataFetcher()
    df = fetcher.fetch_data(resolved, period="1mo", interval="1h")

    if df is None or len(df) < 50:
        return f"❌ لا توجد بيانات كافية لـ {resolved}"

    engine = DecisionEngine(df, resolved)
    analysis = engine.analyze()

    return format_analysis(resolved, analysis)


def run_bot(token: str):
    """Run the bot"""
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['start', 'help', 'ابدأ'])
    def start(message):
        msg = """🎯 *محرك قرارات السوق*
_6 مراحل إلزامية للتحليل_

*الأوامر:*
/gold - الذهب
/btc - البيتكوين
/eurusd - يورو/دولار
/scan - فحص الأسواق

*المراحل الست:*
1️⃣ السياق (الاتجاه)
2️⃣ الموقع (EMAs)
3️⃣ الزخم (RSI)
4️⃣ السلوك (الشموع)
5️⃣ المستويات (S/R)
6️⃣ المخاطرة (R:R)

*القرارات:*
🟢 تنفيذ - جميع المراحل ناجحة
🟡 استعد - بعض المراحل ناقصة
🔴 انتظر - مرحلة أساسية فاشلة

_الحفاظ على رأس المال أولاً._"""
        bot.reply_to(message, msg, parse_mode='Markdown')

    @bot.message_handler(commands=['gold', 'xauusd', 'ذهب'])
    def gold(message):
        bot.reply_to(message, "⏳ جاري التحليل بالمراحل الست...")
        result = analyze_market('gold')
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    @bot.message_handler(commands=['btc', 'bitcoin', 'بتكوين'])
    def btc(message):
        bot.reply_to(message, "⏳ جاري التحليل بالمراحل الست...")
        result = analyze_market('btc')
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    @bot.message_handler(commands=['eurusd'])
    def eurusd(message):
        bot.reply_to(message, "⏳ جاري التحليل بالمراحل الست...")
        result = analyze_market('eurusd')
        bot.send_message(message.chat.id, result, parse_mode='Markdown')

    @bot.message_handler(commands=['gbpusd'])
    def gbpusd(message):
        bot.reply_to(message, "⏳ جاري التحليل بالمراحل الست...")
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

                # Count passed stages
                stages = [
                    analysis.stage1_context,
                    analysis.stage2_location,
                    analysis.stage3_momentum,
                    analysis.stage4_behavior,
                    analysis.stage5_technical,
                    analysis.stage6_risk
                ]
                passed = sum(1 for s in stages if s.passed)

                icon = "🟢" if analysis.decision == Decision.EXECUTE else "🟡" if analysis.decision == Decision.PREPARE else "🔴"
                decision_ar = DECISION_AR.get(analysis.decision, analysis.decision.value)

                results.append(f"{icon} *{name}* | {decision_ar} | {passed}/6 مراحل")

        msg = "📊 *فحص الأسواق*\n\n" + "\n".join(results)
        msg += "\n\n_استخدم الأمر المحدد للتحليل الكامل_"
        bot.send_message(message.chat.id, msg, parse_mode='Markdown')

    print("Bot is running with 6-stage analysis...")
    bot.infinity_polling()


if __name__ == "__main__":
    token = os.environ.get('TELEGRAM_BOT_TOKEN')

    if not token:
        print("Set TELEGRAM_BOT_TOKEN environment variable")
    else:
        run_bot(token)
