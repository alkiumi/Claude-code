#!/usr/bin/env python3
"""
Telegram Bot - Simple Trading Analyzer
⚡ Scalping (M5/M15) + 📊 Full Analysis (MTF)
Stable version with auto-reconnect
"""
import os
import sys
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import telebot
from telebot import apihelper
from mtf_analyzer import MTFDecisionEngine, Decision, Direction
from scalping import create_scalping_engine

# Increase timeout for requests
apihelper.RETRY_ON_ERROR = True
apihelper.READ_TIMEOUT = 30


def format_analysis(result, account_balance: float = 100) -> str:
    """Format MTF analysis with $100 budget calculations"""
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

    # Trade plan with $100 budget
    if result.decision == Decision.EXECUTE and result.direction:
        d = "🟢 شراء" if result.direction == Direction.BUY else "🔴 بيع"
        current_price = result.m5.price if result.m5 else 0

        if result.stop_loss and current_price > 0:
            risk_points = abs(current_price - result.stop_loss)
            risk_usd = account_balance * 0.02

            if 'BTC' in result.symbol:
                lot_size = max(0.001, round(risk_usd / risk_points, 4)) if risk_points > 0 else 0.001
            else:
                lot_size = max(0.01, round(risk_usd / (risk_points * 10), 2)) if risk_points > 0 else 0.01

            # Calculate 3 targets
            tp1 = current_price + risk_points if result.direction == Direction.BUY else current_price - risk_points
            tp2 = current_price + (risk_points * 1.5) if result.direction == Direction.BUY else current_price - (risk_points * 1.5)
            tp3 = current_price + (risk_points * 2) if result.direction == Direction.BUY else current_price - (risk_points * 2)

            msg += f"\n*{d}*\n"
            msg += f"```\n"
            msg += f"الدخول:  {current_price:.2f}\n"
            msg += f"وقف:     {result.stop_loss:.2f}\n"
            msg += f"هدف 1:   {tp1:.2f}\n"
            msg += f"هدف 2:   {tp2:.2f}\n"
            msg += f"هدف 3:   {tp3:.2f}\n"
            msg += f"اللوت:   {lot_size}\n"
            msg += f"```\n"

    return msg


def run_bot(token: str):
    """Run bot with auto-reconnect"""
    bot = telebot.TeleBot(token, threaded=False)
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

    @bot.message_handler(commands=['scalp'])
    def scalp(message):
        bot.reply_to(message, "⚡ جاري الفحص...")
        try:
            bot.send_message(message.chat.id, scalper.quick_scan(), parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Scalp error: {e}")
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
            logger.error(f"S command error: {e}")
            bot.send_message(message.chat.id, f"❌ {e}")

    @bot.message_handler(commands=['btc'])
    def btc(message):
        bot.reply_to(message, "📊 تحليل BTC...")
        try:
            result = MTFDecisionEngine('BTC-USD').analyze()
            bot.send_message(message.chat.id, format_analysis(result), parse_mode='Markdown')
        except Exception as e:
            logger.error(f"BTC error: {e}")
            bot.send_message(message.chat.id, f"❌ {e}")

    @bot.message_handler(commands=['gold'])
    def gold(message):
        bot.reply_to(message, "📊 تحليل GOLD...")
        try:
            result = MTFDecisionEngine('GC=F').analyze()
            bot.send_message(message.chat.id, format_analysis(result), parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Gold error: {e}")
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

    # Main polling loop with reconnect
    logger.info("Bot starting...")
    print("Bot running...")

    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Polling error: {e}")
            print(f"Error: {e}")
            print("Reconnecting in 10 seconds...")
            time.sleep(10)
            continue


if __name__ == "__main__":
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if token:
        run_bot(token)
    else:
        print("Set TELEGRAM_BOT_TOKEN")
