#!/usr/bin/env python3
"""
Telegram Bot - Trading Analyzer (Stable Version)
"""
import os
import sys
import time
import traceback

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

import telebot

# Get token
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("ERROR: Set TELEGRAM_BOT_TOKEN")
    sys.exit(1)

# Create bot
bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

# Lazy load heavy modules
scalper = None
def get_scalper():
    global scalper
    if scalper is None:
        from scalping import create_scalping_engine
        scalper = create_scalping_engine()
    return scalper

@bot.message_handler(commands=['start', 'help'])
def cmd_help(msg):
    bot.reply_to(msg, """🎯 *محلل التداول*

⚡ *سكالبينج:*
/s BTC - بيتكوين
/s GOLD - ذهب
/scalp - فحص الكل

📊 *تحليل:*
/btc - تحليل البيتكوين
/gold - تحليل الذهب""")

@bot.message_handler(commands=['s'])
def cmd_scalp_asset(msg):
    try:
        parts = msg.text.split()
        asset = parts[1].upper() if len(parts) > 1 else 'BTC'

        bot.reply_to(msg, f"⚡ تحليل {asset}...")

        engine = get_scalper()
        opp = engine.analyze_scalp(asset, 'M15')

        if opp:
            bot.send_message(msg.chat.id, engine.format_opportunity(opp))
        else:
            bot.send_message(msg.chat.id, f"📭 لا توجد فرصة لـ {asset}")
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['scalp'])
def cmd_scalp_all(msg):
    try:
        bot.reply_to(msg, "⚡ جاري الفحص...")
        engine = get_scalper()
        bot.send_message(msg.chat.id, engine.quick_scan())
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['btc'])
def cmd_btc(msg):
    try:
        bot.reply_to(msg, "📊 تحليل BTC...")
        from mtf_analyzer import MTFDecisionEngine, Decision, Direction
        result = MTFDecisionEngine('BTC-USD').analyze()

        # Simple format
        icon = "🟢" if result.decision == Decision.EXECUTE else "🟡" if result.decision == Decision.PREPARE else "🔴"
        text = f"{icon} *BTC-USD*\n"
        text += f"التوافق: {result.alignment_score}/4\n"
        text += f"الاتجاه: {result.overall_bias.value}\n"

        if result.decision == Decision.EXECUTE:
            d = "شراء" if result.direction == Direction.BUY else "بيع"
            text += f"\n*الصفقة: {d}*\n"
            if result.m5:
                text += f"السعر: `{result.m5.price:.2f}`\n"
            if result.stop_loss:
                text += f"الوقف: `{result.stop_loss:.2f}`\n"
            if result.target:
                text += f"الهدف: `{result.target:.2f}`\n"

        bot.send_message(msg.chat.id, text)
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ خطأ: {e}")

@bot.message_handler(commands=['gold'])
def cmd_gold(msg):
    try:
        bot.reply_to(msg, "📊 تحليل GOLD...")
        from mtf_analyzer import MTFDecisionEngine, Decision, Direction
        result = MTFDecisionEngine('GC=F').analyze()

        icon = "🟢" if result.decision == Decision.EXECUTE else "🟡" if result.decision == Decision.PREPARE else "🔴"
        text = f"{icon} *GOLD*\n"
        text += f"التوافق: {result.alignment_score}/4\n"
        text += f"الاتجاه: {result.overall_bias.value}\n"

        if result.decision == Decision.EXECUTE:
            d = "شراء" if result.direction == Direction.BUY else "بيع"
            text += f"\n*الصفقة: {d}*\n"
            if result.m5:
                text += f"السعر: `{result.m5.price:.2f}`\n"
            if result.stop_loss:
                text += f"الوقف: `{result.stop_loss:.2f}`\n"
            if result.target:
                text += f"الهدف: `{result.target:.2f}`\n"

        bot.send_message(msg.chat.id, text)
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ خطأ: {e}")

def main():
    print("Bot starting...")

    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Polling...")
            bot.polling(non_stop=False, interval=2, timeout=30)
        except KeyboardInterrupt:
            print("Stopped by user")
            break
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
