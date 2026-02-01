#!/usr/bin/env python3
"""
Telegram Bot - Multi-Timeframe Decision Engine
H4 → H1 → M15 → M5
+ Smart Alerts System
+ Scalping Engine (M5/M15)
"""
import os
import telebot
from mtf_analyzer import MTFDecisionEngine, Decision, Direction
from smart_alerts import create_alert_manager, AlertTrigger
from scalping import create_scalping_engine


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

    # AI/ML Analysis
    if hasattr(result, 'ai_analysis') and result.ai_analysis:
        ai = result.ai_analysis
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
        msg += "*🤖 تحليل الذكاء الاصطناعي:*\n\n"

        # Fear & Greed
        fng = ai.sentiment.fear_greed_index
        fng_emoji = "😱" if fng < 25 else "😰" if fng < 45 else "😐" if fng < 55 else "😊" if fng < 75 else "🤑"
        msg += f"*مؤشر الخوف/الطمع:* {fng_emoji} {fng}/100 ({ai.sentiment.fear_greed_label.value})\n"

        # Sentiment Score
        sent_score = ai.sentiment.sentiment_score
        sent_bar = "🟢" * int((sent_score + 100) / 40) + "⚪" * (5 - int((sent_score + 100) / 40))
        msg += f"*المشاعر:* {sent_bar} ({sent_score:+.0f})\n"

        # Patterns
        if ai.patterns.patterns_found:
            patterns_str = ", ".join([p.value for p, _ in ai.patterns.patterns_found[:3]])
            msg += f"*الأنماط:* {patterns_str}\n"
            msg += f"*اتجاه الأنماط:* {ai.patterns.pattern_bias}\n"

        # ML Prediction
        msg += f"\n*التنبؤ:* {ai.ml_prediction.trend_prediction.value}\n"
        msg += f"*الثقة:* {ai.ml_prediction.confidence:.0f}%\n"

        # Support/Resistance
        if ai.ml_prediction.support_levels:
            support_str = ", ".join([f"{s:.0f}" for s in ai.ml_prediction.support_levels[:2]])
            msg += f"*الدعم:* {support_str}\n"
        if ai.ml_prediction.resistance_levels:
            resist_str = ", ".join([f"{r:.0f}" for r in ai.ml_prediction.resistance_levels[:2]])
            msg += f"*المقاومة:* {resist_str}\n"

        # AI Recommendation
        msg += f"\n{ai.ai_recommendation}\n"
        msg += f"*درجة AI:* {ai.ai_score:+.0f}/100\n"

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
        msg = """🎯 *محرك القرارات الذكي*
_Smart Trading Decision Engine_

*📊 التحليل الكامل (MTF):*
/btc - تحليل البيتكوين
/gold - تحليل الذهب
/scan - فحص جميع الأسواق

*⚡ السكالبينج (M5/M15):*
/scalp - فحص سريع لجميع الأصول
/s BTC - سكالبينج سريع
/s GOLD M5 - سكالبينج M5
/scalp\_btc - بيتكوين
/scalp\_gold - الذهب
/scalp\_eurusd - يورو/دولار
/scalp\_oil - النفط
/scalp\_m5 - فحص M5

*🔔 التنبيهات:*
/alerts - التنبيهات النشطة
/alert\_price BTC 100000 above
/alert\_execute BTC
/alert\_start - تشغيل المسح

*الأصول المدعومة:*
₿ BTC | 🥇 GOLD | 💶 EUR/USD | 🛢️ OIL

*القرارات:*
🟢🟢 شراء قوي | 🔴🔴 بيع قوي
🟢 شراء | 🔴 بيع
⚪ محايد - انتظر

_⚡ السكالبينج = سرعة + انضباط_"""
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

    # ============ SMART ALERTS SYSTEM ============

    # Initialize alert manager
    alert_manager = create_alert_manager(scan_interval=300)  # 5 minutes
    user_chats = {}  # Store user chat IDs

    # Alert notification callback
    def send_alert_notification(trigger: AlertTrigger):
        """Send alert notification to user"""
        user_id = trigger.alert.user_id
        if user_id and user_id in user_chats:
            chat_id = user_chats[user_id]
            try:
                msg = f"🚨 *تنبيه!*\n\n"
                msg += f"*{trigger.alert.symbol}*\n"
                msg += f"{trigger.message}\n\n"
                msg += f"⏰ {trigger.trigger_time[:19]}"
                bot.send_message(chat_id, msg, parse_mode='Markdown')
            except Exception as e:
                print(f"Error sending alert: {e}")

    alert_manager.add_notification_callback(send_alert_notification)

    @bot.message_handler(commands=['alerts'])
    def list_alerts(message):
        """List all active alerts"""
        user_id = str(message.from_user.id)
        user_chats[user_id] = message.chat.id

        msg = alert_manager.format_alerts_list(user_id=user_id)
        bot.reply_to(message, msg, parse_mode='Markdown')

    @bot.message_handler(commands=['alert_price'])
    def create_price_alert(message):
        """Create price alert: /alert_price BTC 100000 above"""
        user_id = str(message.from_user.id)
        user_chats[user_id] = message.chat.id

        parts = message.text.split()
        if len(parts) < 4:
            bot.reply_to(message,
                "الاستخدام: `/alert_price SYMBOL PRICE above/below`\n"
                "مثال: `/alert_price BTC 100000 above`",
                parse_mode='Markdown')
            return

        try:
            symbol = parts[1].upper()
            if symbol == 'BTC':
                symbol = 'BTC-USD'
            elif symbol == 'GOLD':
                symbol = 'GC=F'

            price = float(parts[2])
            above = parts[3].lower() in ['above', 'فوق', 'up', '1']

            alert_id = alert_manager.create_price_alert(
                symbol=symbol, price=price, above=above, user_id=user_id
            )

            direction = "فوق ⬆️" if above else "تحت ⬇️"
            bot.reply_to(message,
                f"✅ تم إنشاء تنبيه السعر\n\n"
                f"🔔 `{alert_id[:8]}`\n"
                f"📊 {symbol}\n"
                f"💰 {direction} {price:,.2f}",
                parse_mode='Markdown')
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['alert_rsi'])
    def create_rsi_alert(message):
        """Create RSI alert: /alert_rsi BTC overbought"""
        user_id = str(message.from_user.id)
        user_chats[user_id] = message.chat.id

        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message,
                "الاستخدام: `/alert_rsi SYMBOL overbought/oversold`\n"
                "مثال: `/alert_rsi BTC oversold`",
                parse_mode='Markdown')
            return

        try:
            symbol = parts[1].upper()
            if symbol == 'BTC':
                symbol = 'BTC-USD'

            overbought = parts[2].lower() in ['overbought', 'تشبع_شرائي', 'ob', '1']

            alert_id = alert_manager.create_rsi_alert(
                symbol=symbol, overbought=overbought, user_id=user_id, repeat=True
            )

            condition = "تشبع شرائي 🔴" if overbought else "تشبع بيعي 🟢"
            bot.reply_to(message,
                f"✅ تم إنشاء تنبيه RSI\n\n"
                f"🔔 `{alert_id[:8]}`\n"
                f"📊 {symbol}\n"
                f"📈 {condition}",
                parse_mode='Markdown')
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['alert_execute'])
    def create_execute_alert(message):
        """Create EXECUTE decision alert: /alert_execute BTC"""
        user_id = str(message.from_user.id)
        user_chats[user_id] = message.chat.id

        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message,
                "الاستخدام: `/alert_execute SYMBOL`\n"
                "مثال: `/alert_execute BTC`",
                parse_mode='Markdown')
            return

        try:
            symbol = parts[1].upper()
            if symbol == 'BTC':
                symbol = 'BTC-USD'
            elif symbol == 'GOLD':
                symbol = 'GC=F'

            alert_id = alert_manager.create_decision_alert(
                symbol=symbol, to_decision='EXECUTE', user_id=user_id, repeat=True
            )

            bot.reply_to(message,
                f"✅ تم إنشاء تنبيه التنفيذ\n\n"
                f"🔔 `{alert_id[:8]}`\n"
                f"📊 {symbol}\n"
                f"🟢 تنبيه عند قرار التنفيذ",
                parse_mode='Markdown')
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['alert_ai'])
    def create_ai_alert(message):
        """Create AI signal alert: /alert_ai BTC buy"""
        user_id = str(message.from_user.id)
        user_chats[user_id] = message.chat.id

        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message,
                "الاستخدام: `/alert_ai SYMBOL buy/sell/any`\n"
                "مثال: `/alert_ai BTC buy`",
                parse_mode='Markdown')
            return

        try:
            symbol = parts[1].upper()
            if symbol == 'BTC':
                symbol = 'BTC-USD'

            direction = parts[2].lower()
            if direction in ['شراء', 'buy']:
                direction = 'buy'
            elif direction in ['بيع', 'sell']:
                direction = 'sell'
            else:
                direction = 'any'

            alert_id = alert_manager.create_ai_signal_alert(
                symbol=symbol, threshold=40, direction=direction, user_id=user_id, repeat=True
            )

            dir_ar = {'buy': 'شراء 📈', 'sell': 'بيع 📉', 'any': 'أي اتجاه'}
            bot.reply_to(message,
                f"✅ تم إنشاء تنبيه AI\n\n"
                f"🔔 `{alert_id[:8]}`\n"
                f"📊 {symbol}\n"
                f"🤖 إشارة {dir_ar.get(direction, direction)}",
                parse_mode='Markdown')
        except Exception as e:
            bot.reply_to(message, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['alert_delete', 'del_alert'])
    def delete_alert(message):
        """Delete alert: /alert_delete ALERT_ID"""
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message,
                "الاستخدام: `/alert_delete ALERT_ID`\n"
                "مثال: `/alert_delete abc123`",
                parse_mode='Markdown')
            return

        alert_id = parts[1]

        # Find full ID if partial
        all_alerts = alert_manager.storage.alerts
        full_id = None
        for aid in all_alerts:
            if aid.startswith(alert_id):
                full_id = aid
                break

        if full_id and alert_manager.delete_alert(full_id):
            bot.reply_to(message, f"✅ تم حذف التنبيه `{alert_id}`", parse_mode='Markdown')
        else:
            bot.reply_to(message, f"❌ لم يتم العثور على التنبيه")

    @bot.message_handler(commands=['alert_check'])
    def check_alerts_now(message):
        """Manually check all alerts now"""
        user_id = str(message.from_user.id)
        user_chats[user_id] = message.chat.id

        bot.reply_to(message, "⏳ جاري فحص التنبيهات...")

        try:
            triggered = alert_manager.check_now()
            if triggered:
                msg = f"🚨 *تم تفعيل {len(triggered)} تنبيه(ات)*\n\n"
                for t in triggered:
                    msg += f"• {t.alert.symbol}: {t.message}\n"
                bot.send_message(message.chat.id, msg, parse_mode='Markdown')
            else:
                bot.send_message(message.chat.id, "✅ لا توجد تنبيهات مفعّلة حالياً")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['alert_start'])
    def start_scanner(message):
        """Start background alert scanner"""
        user_id = str(message.from_user.id)
        user_chats[user_id] = message.chat.id

        alert_manager.start_scanner()
        bot.reply_to(message,
            "✅ تم تشغيل المسح التلقائي للتنبيهات\n"
            "⏱️ الفحص كل 5 دقائق")

    @bot.message_handler(commands=['alert_stop'])
    def stop_scanner(message):
        """Stop background alert scanner"""
        alert_manager.stop_scanner()
        bot.reply_to(message, "⏹️ تم إيقاف المسح التلقائي")

    # ============ SCALPING SYSTEM ============

    scalping_engine = create_scalping_engine()

    @bot.message_handler(commands=['scalp', 'سكالب'])
    def scalp_scan(message):
        """Quick scalp scan all assets"""
        bot.reply_to(message, "⚡ جاري فحص فرص السكالبينج...")

        try:
            msg = scalping_engine.quick_scan()
            bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['scalp_btc', 'سكالب_بتكوين'])
    def scalp_btc(message):
        """Scalp analysis for BTC"""
        bot.reply_to(message, "⚡ جاري تحليل سكالبينج البيتكوين...")

        try:
            opp = scalping_engine.analyze_scalp('BTC', 'M15')
            if opp:
                msg = scalping_engine.format_opportunity(opp)
            else:
                msg = "📭 لا توجد فرصة سكالبينج للبيتكوين حالياً\n_جرب لاحقاً أو راقب الفريمات الأصغر_"
            bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['scalp_gold', 'سكالب_ذهب'])
    def scalp_gold(message):
        """Scalp analysis for Gold"""
        bot.reply_to(message, "⚡ جاري تحليل سكالبينج الذهب...")

        try:
            opp = scalping_engine.analyze_scalp('GOLD', 'M15')
            if opp:
                msg = scalping_engine.format_opportunity(opp)
            else:
                msg = "📭 لا توجد فرصة سكالبينج للذهب حالياً\n_جرب لاحقاً أو راقب الفريمات الأصغر_"
            bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['scalp_eurusd', 'سكالب_يورو'])
    def scalp_eurusd(message):
        """Scalp analysis for EUR/USD"""
        bot.reply_to(message, "⚡ جاري تحليل سكالبينج EUR/USD...")

        try:
            opp = scalping_engine.analyze_scalp('EURUSD', 'M15')
            if opp:
                msg = scalping_engine.format_opportunity(opp)
            else:
                msg = "📭 لا توجد فرصة سكالبينج لـ EUR/USD حالياً\n_جرب لاحقاً أو راقب الفريمات الأصغر_"
            bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['scalp_oil', 'سكالب_نفط'])
    def scalp_oil(message):
        """Scalp analysis for Oil"""
        bot.reply_to(message, "⚡ جاري تحليل سكالبينج النفط...")

        try:
            opp = scalping_engine.analyze_scalp('OIL', 'M15')
            if opp:
                msg = scalping_engine.format_opportunity(opp)
            else:
                msg = "📭 لا توجد فرصة سكالبينج للنفط حالياً\n_جرب لاحقاً أو راقب الفريمات الأصغر_"
            bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['scalp_m5'])
    def scalp_m5(message):
        """Quick scalp scan on M5 timeframe"""
        bot.reply_to(message, "⚡ جاري فحص فرص السكالبينج (M5)...")

        try:
            scan = scalping_engine.scan_all_assets('M5')

            msg = f"⚡ *فحص السكالبينج - M5*\n"
            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"حالة السوق: {scan.market_condition}\n\n"

            if scan.opportunities:
                for opp in scan.opportunities:
                    icon = '🟢' if 'BUY' in opp.signal.value else '🔴'
                    msg += f"{icon} *{opp.symbol}*: {opp.signal.value}\n"
                    msg += f"   الثقة: {opp.confidence:.0f}% | {opp.urgency}\n\n"
            else:
                msg += "📭 لا توجد فرص حالياً"

            bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")

    @bot.message_handler(commands=['s'])
    def quick_scalp(message):
        """Quick scalp command: /s BTC or /s GOLD"""
        parts = message.text.split()
        if len(parts) < 2:
            # Default to quick scan
            bot.reply_to(message, "⚡ جاري الفحص السريع...")
            try:
                msg = scalping_engine.quick_scan()
                bot.send_message(message.chat.id, msg, parse_mode='Markdown')
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ خطأ: {str(e)}")
            return

        asset = parts[1].upper()
        timeframe = parts[2].upper() if len(parts) > 2 else 'M15'

        if timeframe not in ['M5', 'M15']:
            timeframe = 'M15'

        bot.reply_to(message, f"⚡ جاري تحليل {asset} ({timeframe})...")

        try:
            opp = scalping_engine.analyze_scalp(asset, timeframe)
            if opp:
                msg = scalping_engine.format_opportunity(opp)
            else:
                msg = f"📭 لا توجد فرصة سكالبينج لـ {asset} حالياً"
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
