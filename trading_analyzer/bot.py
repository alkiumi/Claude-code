#!/usr/bin/env python3
"""
Telegram Bot - Trading Analyzer
"""
import os
import sys
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

import telebot

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    print("ERROR: Set TELEGRAM_BOT_TOKEN")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

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

        icon = "🟢" if result.decision == Decision.EXECUTE else "🟡" if result.decision == Decision.PREPARE else "🔴"
        d_text = "تنفيذ" if result.decision == Decision.EXECUTE else "استعد" if result.decision == Decision.PREPARE else "انتظر"

        text = f"{icon} *{d_text}*\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"*BTC-USD*\n"
        text += f"التوافق: {result.alignment_score}/4\n"
        text += f"الاتجاه: {result.overall_bias.value}\n\n"

        # Always show trade details if there's a direction
        if result.overall_bias != Direction.NEUTRAL:
            direction = "شراء 🟢" if result.overall_bias == Direction.BUY else "بيع 🔴"
            price = result.m5.price if result.m5 else 0

            if price > 0:
                # Calculate levels based on ATR
                atr = result.m5.atr if result.m5 else price * 0.01

                if result.overall_bias == Direction.BUY:
                    entry = price
                    sl = price - (atr * 1.5)
                    tp1 = price + (atr * 1.0)
                    tp2 = price + (atr * 1.5)
                    tp3 = price + (atr * 2.0)
                else:
                    entry = price
                    sl = price + (atr * 1.5)
                    tp1 = price - (atr * 1.0)
                    tp2 = price - (atr * 1.5)
                    tp3 = price - (atr * 2.0)

                text += f"*الصفقة: {direction}*\n"
                text += f"```\n"
                text += f"الدخول:  {entry:.2f}\n"
                text += f"━━━━━━━━━━━━━━━━\n"
                text += f"هدف 1:   {tp1:.2f}\n"
                text += f"هدف 2:   {tp2:.2f}\n"
                text += f"هدف 3:   {tp3:.2f}\n"
                text += f"━━━━━━━━━━━━━━━━\n"
                text += f"وقف:     {sl:.2f}\n"
                text += f"━━━━━━━━━━━━━━━━\n"
                text += f"اللوت:   0.01\n"
                text += f"```\n"

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
        d_text = "تنفيذ" if result.decision == Decision.EXECUTE else "استعد" if result.decision == Decision.PREPARE else "انتظر"

        text = f"{icon} *{d_text}*\n"
        text += f"━━━━━━━━━━━━━━━━━━━━\n"
        text += f"*GOLD*\n"
        text += f"التوافق: {result.alignment_score}/4\n"
        text += f"الاتجاه: {result.overall_bias.value}\n\n"

        # Always show trade details if there's a direction
        if result.overall_bias != Direction.NEUTRAL:
            direction = "شراء 🟢" if result.overall_bias == Direction.BUY else "بيع 🔴"
            price = result.m5.price if result.m5 else 0

            if price > 0:
                # Calculate levels based on ATR
                atr = result.m5.atr if result.m5 else price * 0.005

                if result.overall_bias == Direction.BUY:
                    entry = price
                    sl = price - (atr * 1.5)
                    tp1 = price + (atr * 1.0)
                    tp2 = price + (atr * 1.5)
                    tp3 = price + (atr * 2.0)
                else:
                    entry = price
                    sl = price + (atr * 1.5)
                    tp1 = price - (atr * 1.0)
                    tp2 = price - (atr * 1.5)
                    tp3 = price - (atr * 2.0)

                text += f"*الصفقة: {direction}*\n"
                text += f"```\n"
                text += f"الدخول:  {entry:.2f}\n"
                text += f"━━━━━━━━━━━━━━━━\n"
                text += f"هدف 1:   {tp1:.2f}\n"
                text += f"هدف 2:   {tp2:.2f}\n"
                text += f"هدف 3:   {tp3:.2f}\n"
                text += f"━━━━━━━━━━━━━━━━\n"
                text += f"وقف:     {sl:.2f}\n"
                text += f"━━━━━━━━━━━━━━━━\n"
                text += f"اللوت:   0.01\n"
                text += f"```\n"

        bot.send_message(msg.chat.id, text)
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ خطأ: {e}")

def main():
    print("Bot starting...")
    # Clear any pending updates first
    try:
        bot.get_updates(offset=-1, timeout=1)
    except:
        pass

    while True:
        try:
            print(f"[{time.strftime('%H:%M:%S')}] Polling...")
            bot.polling(non_stop=False, interval=3, timeout=60, skip_pending=True)
        except KeyboardInterrupt:
            print("Stopped")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
