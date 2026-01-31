#!/usr/bin/env python3
"""
Telegram Bot - Multi-Timeframe Decision Engine
H4 → H1 → M15 → M5
"""
import os
import telebot
from mtf_analyzer import MTFDecisionEngine, Decision, Direction


DECISION_AR = {
    Decision.EXECUTE: "تنفيذ",
    Decision.PREPARE: "استعد",
    Decision.WAIT: "انتظر",
}


def format_tf_row(tf_name: str, tf_data) -> str:
    """Format a single timeframe row"""
    if tf_data is None:
        return f"| {tf_name} | ❓ | — | — | — |"

    trend_icon = "🟢" if tf_data.bias == Direction.BUY else "🔴" if tf_data.bias == Direction.SELL else "⚪"

    return f"| {tf_name} | {trend_icon} {tf_data.trend.value} | {tf_data.price:.2f} | {tf_data.rsi:.0f} | {tf_data.price_vs_ema20:+.1f} |"


def format_stage(stage) -> str:
    """Format a single stage"""
    icon = "✅" if stage.passed else "❌"

    text = f"*المرحلة {stage.stage_num} - {stage.name}*\n"
    text += f"{icon} {stage.summary}\n"
    text += f"`H4:{stage.h4_status[:15]}`\n"
    text += f"`H1:{stage.h1_status[:15]}`\n"
    text += f"`M15:{stage.m15_status[:15]}`\n"
    text += f"`M5:{stage.m5_status[:15]}`\n"

    for detail in stage.details[:2]:
        text += f"  • {detail}\n"

    return text


def format_mtf_analysis(result) -> str:
    """Format complete MTF analysis"""

    # Decision header
    if result.decision == Decision.EXECUTE:
        decision_icon = "🟢"
    elif result.decision == Decision.PREPARE:
        decision_icon = "🟡"
    else:
        decision_icon = "🔴"

    decision_ar = DECISION_AR.get(result.decision, result.decision.value)

    msg = f"{decision_icon} *{decision_ar}*\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"*{result.symbol}*\n"
    msg += f"📊 التوافق: {result.alignment_score}/4 فريمات\n"
    msg += f"🧭 الاتجاه: {result.overall_bias.value}\n"
    msg += f"⏰ {result.fetch_time}\n"

    # Show data sources
    if hasattr(result, 'sources_used') and result.sources_used:
        sources_str = ', '.join(result.sources_used)
        msg += f"📡 المصادر: `{sources_str}`\n"

    msg += "\n"

    # Timeframe summary table
    msg += "*تحليل الفريمات:*\n"
    msg += "```\n"
    msg += "| TF  | Trend | Price | RSI | EMA20 |\n"
    msg += "|-----|-------|-------|-----|-------|\n"

    for tf_name, tf_data in [('H4', result.h4), ('H1', result.h1), ('M15', result.m15), ('M5', result.m5)]:
        if tf_data:
            trend_s = tf_data.trend.value[:6]
            msg += f"| {tf_name} | {trend_s} | {tf_data.price:.0f} | {tf_data.rsi:.0f} | {tf_data.price_vs_ema20:+.1f} |\n"
        else:
            msg += f"| {tf_name} | — | — | — | — |\n"

    msg += "```\n\n"

    # 6 Stages
    stages = [
        result.stage1_context,
        result.stage2_location,
        result.stage3_momentum,
        result.stage4_behavior,
        result.stage5_levels,
        result.stage6_risk
    ]

    passed_count = sum(1 for s in stages if s.passed)
    msg += f"*المراحل الست:* {passed_count}/6 ✅\n\n"

    for stage in stages:
        icon = "✅" if stage.passed else "❌"
        msg += f"{icon} *{stage.stage_num}. {stage.name}*: {stage.summary}\n"

    msg += "\n"

    # Trade plan if EXECUTE
    if result.decision == Decision.EXECUTE and result.direction:
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
        msg += "*خطة الصفقة:*\n"
        dir_icon = "🟢" if result.direction == Direction.BUY else "🔴"
        msg += f"`الاتجاه:      {dir_icon} {result.direction.value}`\n"
        if result.entry_zone:
            msg += f"`الدخول:      {result.entry_zone[0]:.2f} - {result.entry_zone[1]:.2f}`\n"
        if result.stop_loss:
            msg += f"`وقف الخسارة: {result.stop_loss:.2f}`\n"
        if result.target:
            msg += f"`الهدف:       {result.target:.2f}`\n"
        if result.risk_reward:
            msg += f"`المخاطرة:    1:{result.risk_reward}`\n"
        if result.hold_time:
            msg += f"`المدة:       {result.hold_time}`\n"

    # Footer
    msg += "\n━━━━━━━━━━━━━━━━━━━━\n"
    if result.decision == Decision.WAIT:
        msg += "_عدم التداول قرار صحيح._"
    elif result.decision == Decision.PREPARE:
        msg += "_راقب وانتظر توافق الفريمات._"
    else:
        msg += "_الحفاظ على رأس المال أولاً._"

    return msg


def run_bot(token: str):
    """Run the bot"""
    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['start', 'help'])
    def start(message):
        msg = """🎯 *محرك القرارات متعدد الفريمات*
_Multi-Timeframe Decision Engine_

*الفريمات:*
H4 → السياق الأكبر
H1 → الاتجاه
M15 → القرار
M5 → التوقيت

*الأوامر:*
/btc - تحليل البيتكوين
/gold - تحليل الذهب
/eurusd - تحليل EUR/USD
/scan - فحص جميع الأسواق

*القرارات:*
🟢 تنفيذ - 4/4 فريمات + 5/6 مراحل
🟡 استعد - توافق جزئي
🔴 انتظر - لا توافق

*المراحل الست:*
1️⃣ السياق (H4+H1)
2️⃣ الموقع (EMAs)
3️⃣ الزخم (RSI)
4️⃣ السلوك (الشموع)
5️⃣ المستويات (S/R)
6️⃣ المخاطرة (R:R)

_الحفاظ على رأس المال أولاً._"""
        bot.reply_to(message, msg, parse_mode='Markdown')

    @bot.message_handler(commands=['btc', 'bitcoin'])
    def btc(message):
        bot.reply_to(message, "⏳ جاري تحليل البيتكوين (4 فريمات)...")
        try:
            engine = MTFDecisionEngine('BTC-USD')
            result = engine.analyze()
            msg = format_mtf_analysis(result)
            bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['gold', 'xauusd'])
    def gold(message):
        bot.reply_to(message, "⏳ جاري تحليل الذهب (4 فريمات)...")
        try:
            engine = MTFDecisionEngine('GC=F')
            result = engine.analyze()
            msg = format_mtf_analysis(result)
            bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['eurusd'])
    def eurusd(message):
        bot.reply_to(message, "⏳ جاري تحليل EUR/USD (4 فريمات)...")
        try:
            engine = MTFDecisionEngine('EURUSD=X')
            result = engine.analyze()
            msg = format_mtf_analysis(result)
            bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['scan'])
    def scan(message):
        bot.reply_to(message, "⏳ جاري فحص الأسواق...")

        results = []
        markets = [
            ('BTC-USD', 'البيتكوين'),
            ('GC=F', 'الذهب'),
            ('EURUSD=X', 'EUR/USD')
        ]

        for symbol, name in markets:
            try:
                engine = MTFDecisionEngine(symbol)
                result = engine.analyze()

                icon = "🟢" if result.decision == Decision.EXECUTE else "🟡" if result.decision == Decision.PREPARE else "🔴"
                decision_ar = DECISION_AR.get(result.decision, result.decision.value)

                # Count passed stages
                stages = [
                    result.stage1_context,
                    result.stage2_location,
                    result.stage3_momentum,
                    result.stage4_behavior,
                    result.stage5_levels,
                    result.stage6_risk
                ]
                passed = sum(1 for s in stages if s.passed)

                results.append(
                    f"{icon} *{name}*\n"
                    f"   {decision_ar} | {result.alignment_score}/4 TF | {passed}/6 مراحل"
                )
            except Exception as e:
                results.append(f"❌ *{name}*: خطأ")

        msg = "📊 *فحص الأسواق (MTF)*\n\n" + "\n\n".join(results)
        msg += "\n\n_استخدم الأمر المحدد للتحليل الكامل_"
        bot.send_message(message.chat.id, msg, parse_mode='Markdown')

    @bot.message_handler(commands=['a', 'analyze'])
    def analyze(message):
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "الاستخدام: /a SYMBOL\nمثال: /a AAPL")
            return

        symbol = parts[1].upper()
        bot.reply_to(message, f"⏳ جاري تحليل {symbol} (4 فريمات)...")

        try:
            engine = MTFDecisionEngine(symbol)
            result = engine.analyze()
            msg = format_mtf_analysis(result)
            bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

    print("MTF Bot is running...")
    bot.infinity_polling()


if __name__ == "__main__":
    token = os.environ.get('TELEGRAM_BOT_TOKEN')

    if not token:
        print("Set TELEGRAM_BOT_TOKEN environment variable")
    else:
        run_bot(token)
