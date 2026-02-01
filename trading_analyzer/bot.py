#!/usr/bin/env python3
"""
Telegram Bot - Simple Trading Analyzer
⚡ Scalping (M5/M15) + 📊 Full Analysis (MTF)
Lightweight - Runs only when needed
"""
import os
import telebot
from mtf_analyzer import MTFDecisionEngine, Decision, Direction
from scalping import create_scalping_engine


def format_analysis(result) -> str:
    """Format MTF analysis"""
    if result.decision == Decision.EXECUTE:
        icon, ar = "🟢", "تنفيذ"
    elif result.decision == Decision.PREPARE:
        icon, ar = "🟡", "استعد"
    else:
        icon, ar = "🔴", "انتظر"

    msg = f"{icon} *{ar}*\n━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"*{result.symbol}*\n"
    msg += f"📊 التوافق: {result.alignment_score}/4\n"
    msg += f"🧭 الاتجاه: {result.overall_bias.value}\n\n"

    # Timeframes table
    msg += "```\n"
    msg += "TF  | Trend  | RSI\n"
    msg += "----|--------|----\n"
    for tf, data in [('H4', result.h4), ('H1', result.h1), ('M15', result.m15), ('M5', result.m5)]:
        if data:
            msg += f"{tf}  | {data.trend.value[:6]} | {data.rsi:.0f}\n"
    msg += "```\n\n"

    # Stages
    stages = [result.stage1_context, result.stage2_location, result.stage3_momentum,
              result.stage4_behavior, result.stage5_levels, result.stage6_risk]
    passed = sum(1 for s in stages if s.passed)
    msg += f"*المراحل:* {passed}/6\n"
    for s in stages:
        msg += f"{'✅' if s.passed else '❌'} {s.summary}\n"

    # AI
    if hasattr(result, 'ai_analysis') and result.ai_analysis:
        ai = result.ai_analysis
        fng = ai.sentiment.fear_greed_index
        emoji = "😱" if fng < 25 else "😐" if fng < 55 else "🤑"
        msg += f"\n*AI:* {emoji} خوف/طمع {fng} | {ai.ai_recommendation}\n"

    # Trade plan
    if result.decision == Decision.EXECUTE and result.direction:
        d = "🟢 شراء" if result.direction == Direction.BUY else "🔴 بيع"
        msg += f"\n*الصفقة:* {d}\n"
        if result.stop_loss:
            msg += f"الوقف: `{result.stop_loss:.2f}`\n"
        if result.target:
            msg += f"الهدف: `{result.target:.2f}`\n"

    return msg


def run_bot(token: str):
    bot = telebot.TeleBot(token)
    scalper = create_scalping_engine()

    @bot.message_handler(commands=['start', 'help'])
    def help_cmd(message):
        msg = """🎯 *محلل التداول*

*⚡ سكالبينج (سريع):*
/scalp - فحص الكل
/s BTC - بيتكوين
/s GOLD - ذهب
/s OIL - نفط
/s EURUSD - يورو

*📊 تحليل شامل:*
/btc - البيتكوين
/gold - الذهب

*الإشارات:*
🟢🟢 شراء قوي | 🔴🔴 بيع قوي
🟢 شراء | 🔴 بيع | ⚪ انتظر"""
        bot.reply_to(message, msg, parse_mode='Markdown')

    # === SCALPING ===

    @bot.message_handler(commands=['scalp'])
    def scalp(message):
        bot.reply_to(message, "⚡ جاري الفحص...")
        try:
            bot.send_message(message.chat.id, scalper.quick_scan(), parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ {e}")

    @bot.message_handler(commands=['s'])
    def s_cmd(message):
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚡ فحص...")
            try:
                bot.send_message(message.chat.id, scalper.quick_scan(), parse_mode='Markdown')
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ {e}")
            return

        asset = parts[1].upper()
        tf = parts[2].upper() if len(parts) > 2 and parts[2].upper() in ['M5', 'M15'] else 'M15'

        bot.reply_to(message, f"⚡ {asset}...")
        try:
            opp = scalper.analyze_scalp(asset, tf)
            if opp:
                bot.send_message(message.chat.id, scalper.format_opportunity(opp), parse_mode='Markdown')
            else:
                bot.send_message(message.chat.id, f"📭 لا توجد فرصة لـ {asset}")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ {e}")

    # === FULL ANALYSIS ===

    @bot.message_handler(commands=['btc'])
    def btc(message):
        bot.reply_to(message, "📊 تحليل BTC...")
        try:
            result = MTFDecisionEngine('BTC-USD').analyze()
            bot.send_message(message.chat.id, format_analysis(result), parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ {e}")

    @bot.message_handler(commands=['gold'])
    def gold(message):
        bot.reply_to(message, "📊 تحليل GOLD...")
        try:
            result = MTFDecisionEngine('GC=F').analyze()
            bot.send_message(message.chat.id, format_analysis(result), parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ {e}")

    @bot.message_handler(commands=['scan'])
    def scan(message):
        bot.reply_to(message, "📊 فحص...")
        msg = "*فحص الأسواق:*\n\n"
        for sym, name in [('BTC-USD', 'BTC'), ('GC=F', 'GOLD')]:
            try:
                r = MTFDecisionEngine(sym).analyze()
                icon = "🟢" if r.decision == Decision.EXECUTE else "🟡" if r.decision == Decision.PREPARE else "🔴"
                msg += f"{icon} *{name}*: {r.alignment_score}/4 TF\n"
            except:
                msg += f"❌ *{name}*\n"
        bot.send_message(message.chat.id, msg, parse_mode='Markdown')

    print("Bot running...")
    bot.infinity_polling()


if __name__ == "__main__":
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if token:
        run_bot(token)
    else:
        print("Set TELEGRAM_BOT_TOKEN")
