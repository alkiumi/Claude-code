"""
Smart Alerts System
- Price Alerts (above/below level)
- Technical Alerts (RSI, EMA crossover)
- Pattern Alerts (candlestick patterns)
- Sentiment Alerts (Fear & Greed changes)
- Decision Alerts (WAIT→PREPARE→EXECUTE)
- Market Scanner (periodic scanning)
"""
import json
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import hashlib


class AlertType(Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    RSI_OVERBOUGHT = "rsi_overbought"
    RSI_OVERSOLD = "rsi_oversold"
    EMA_CROSSOVER = "ema_crossover"
    PATTERN_DETECTED = "pattern_detected"
    FEAR_GREED_EXTREME = "fear_greed_extreme"
    DECISION_CHANGE = "decision_change"
    TREND_CHANGE = "trend_change"
    ALIGNMENT_HIGH = "alignment_high"
    AI_SIGNAL = "ai_signal"


class AlertPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AlertStatus(Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class Alert:
    """Single alert configuration"""
    id: str
    alert_type: AlertType
    symbol: str
    condition: Dict[str, Any]
    priority: AlertPriority = AlertPriority.MEDIUM
    status: AlertStatus = AlertStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    triggered_at: Optional[str] = None
    expires_at: Optional[str] = None
    message: str = ""
    repeat: bool = False  # If True, alert reactivates after trigger
    cooldown_minutes: int = 60  # Minimum time between repeated alerts
    last_triggered: Optional[str] = None
    user_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        d = asdict(self)
        d['alert_type'] = self.alert_type.value
        d['priority'] = self.priority.value
        d['status'] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'Alert':
        """Create from dictionary"""
        d['alert_type'] = AlertType(d['alert_type'])
        d['priority'] = AlertPriority(d['priority'])
        d['status'] = AlertStatus(d['status'])
        return cls(**d)


@dataclass
class AlertTrigger:
    """Triggered alert notification"""
    alert: Alert
    trigger_time: str
    trigger_value: Any
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


class AlertStorage:
    """Persistent storage for alerts"""

    def __init__(self, storage_path: str = None):
        if storage_path is None:
            storage_path = os.path.join(os.path.dirname(__file__), 'alerts_data.json')
        self.storage_path = storage_path
        self.alerts: Dict[str, Alert] = {}
        self.load()

    def load(self):
        """Load alerts from file"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.alerts = {
                        aid: Alert.from_dict(a) for aid, a in data.get('alerts', {}).items()
                    }
        except Exception as e:
            print(f"Error loading alerts: {e}")
            self.alerts = {}

    def save(self):
        """Save alerts to file"""
        try:
            data = {
                'alerts': {aid: a.to_dict() for aid, a in self.alerts.items()},
                'last_updated': datetime.utcnow().isoformat()
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving alerts: {e}")

    def add(self, alert: Alert) -> str:
        """Add new alert"""
        self.alerts[alert.id] = alert
        self.save()
        return alert.id

    def remove(self, alert_id: str) -> bool:
        """Remove alert"""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            self.save()
            return True
        return False

    def get(self, alert_id: str) -> Optional[Alert]:
        """Get alert by ID"""
        return self.alerts.get(alert_id)

    def get_active(self, symbol: str = None) -> List[Alert]:
        """Get all active alerts, optionally filtered by symbol"""
        alerts = [a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE]
        if symbol:
            alerts = [a for a in alerts if a.symbol.upper() == symbol.upper()]
        return alerts

    def update_status(self, alert_id: str, status: AlertStatus):
        """Update alert status"""
        if alert_id in self.alerts:
            self.alerts[alert_id].status = status
            if status == AlertStatus.TRIGGERED:
                self.alerts[alert_id].triggered_at = datetime.utcnow().isoformat()
            self.save()


class AlertConditionChecker:
    """Check if alert conditions are met"""

    def __init__(self):
        self.checkers = {
            AlertType.PRICE_ABOVE: self._check_price_above,
            AlertType.PRICE_BELOW: self._check_price_below,
            AlertType.RSI_OVERBOUGHT: self._check_rsi_overbought,
            AlertType.RSI_OVERSOLD: self._check_rsi_oversold,
            AlertType.EMA_CROSSOVER: self._check_ema_crossover,
            AlertType.PATTERN_DETECTED: self._check_pattern,
            AlertType.FEAR_GREED_EXTREME: self._check_fear_greed,
            AlertType.DECISION_CHANGE: self._check_decision_change,
            AlertType.TREND_CHANGE: self._check_trend_change,
            AlertType.ALIGNMENT_HIGH: self._check_alignment,
            AlertType.AI_SIGNAL: self._check_ai_signal,
        }

    def check(self, alert: Alert, market_data: Dict) -> Optional[AlertTrigger]:
        """Check if alert condition is met"""
        checker = self.checkers.get(alert.alert_type)
        if checker:
            return checker(alert, market_data)
        return None

    def _check_price_above(self, alert: Alert, data: Dict) -> Optional[AlertTrigger]:
        """Check if price is above threshold"""
        target_price = alert.condition.get('price', 0)
        current_price = data.get('price', 0)

        if current_price > target_price:
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value=current_price,
                message=f"🔔 السعر تجاوز {target_price:,.2f}\nالسعر الحالي: {current_price:,.2f}",
                details={'target': target_price, 'current': current_price}
            )
        return None

    def _check_price_below(self, alert: Alert, data: Dict) -> Optional[AlertTrigger]:
        """Check if price is below threshold"""
        target_price = alert.condition.get('price', 0)
        current_price = data.get('price', 0)

        if current_price < target_price:
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value=current_price,
                message=f"🔔 السعر انخفض تحت {target_price:,.2f}\nالسعر الحالي: {current_price:,.2f}",
                details={'target': target_price, 'current': current_price}
            )
        return None

    def _check_rsi_overbought(self, alert: Alert, data: Dict) -> Optional[AlertTrigger]:
        """Check if RSI is overbought"""
        threshold = alert.condition.get('threshold', 70)
        rsi = data.get('rsi', 50)

        if rsi > threshold:
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value=rsi,
                message=f"⚠️ تشبع شرائي!\nRSI: {rsi:.1f} (فوق {threshold})",
                details={'threshold': threshold, 'rsi': rsi}
            )
        return None

    def _check_rsi_oversold(self, alert: Alert, data: Dict) -> Optional[AlertTrigger]:
        """Check if RSI is oversold"""
        threshold = alert.condition.get('threshold', 30)
        rsi = data.get('rsi', 50)

        if rsi < threshold:
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value=rsi,
                message=f"⚠️ تشبع بيعي!\nRSI: {rsi:.1f} (تحت {threshold})",
                details={'threshold': threshold, 'rsi': rsi}
            )
        return None

    def _check_ema_crossover(self, alert: Alert, data: Dict) -> Optional[AlertTrigger]:
        """Check for EMA crossover"""
        ema_20 = data.get('ema_20', 0)
        ema_50 = data.get('ema_50', 0)
        prev_ema_20 = data.get('prev_ema_20', 0)
        prev_ema_50 = data.get('prev_ema_50', 0)

        direction = alert.condition.get('direction', 'any')

        # Bullish crossover: EMA20 crosses above EMA50
        bullish_cross = prev_ema_20 <= prev_ema_50 and ema_20 > ema_50
        # Bearish crossover: EMA20 crosses below EMA50
        bearish_cross = prev_ema_20 >= prev_ema_50 and ema_20 < ema_50

        if direction == 'bullish' and bullish_cross:
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value="bullish_crossover",
                message="📈 تقاطع صاعد!\nEMA20 تجاوز EMA50 للأعلى",
                details={'ema_20': ema_20, 'ema_50': ema_50}
            )
        elif direction == 'bearish' and bearish_cross:
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value="bearish_crossover",
                message="📉 تقاطع هابط!\nEMA20 كسر EMA50 للأسفل",
                details={'ema_20': ema_20, 'ema_50': ema_50}
            )
        elif direction == 'any' and (bullish_cross or bearish_cross):
            cross_type = "صاعد 📈" if bullish_cross else "هابط 📉"
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value="bullish_crossover" if bullish_cross else "bearish_crossover",
                message=f"🔄 تقاطع {cross_type}!\nEMA20/EMA50",
                details={'ema_20': ema_20, 'ema_50': ema_50, 'type': cross_type}
            )
        return None

    def _check_pattern(self, alert: Alert, data: Dict) -> Optional[AlertTrigger]:
        """Check for pattern detection"""
        patterns = data.get('patterns', [])
        target_pattern = alert.condition.get('pattern', None)

        if not patterns:
            return None

        for pattern, _ in patterns:
            if target_pattern is None or pattern.value == target_pattern:
                return AlertTrigger(
                    alert=alert,
                    trigger_time=datetime.utcnow().isoformat(),
                    trigger_value=pattern.value,
                    message=f"🎯 نمط مكتشف: {pattern.value}",
                    details={'pattern': pattern.value}
                )
        return None

    def _check_fear_greed(self, alert: Alert, data: Dict) -> Optional[AlertTrigger]:
        """Check Fear & Greed extreme levels"""
        fng = data.get('fear_greed', 50)
        extreme_fear = alert.condition.get('extreme_fear', 20)
        extreme_greed = alert.condition.get('extreme_greed', 80)

        if fng <= extreme_fear:
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value=fng,
                message=f"😱 خوف شديد!\nFear & Greed: {fng}",
                details={'fng': fng, 'level': 'extreme_fear'}
            )
        elif fng >= extreme_greed:
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value=fng,
                message=f"🤑 طمع شديد!\nFear & Greed: {fng}",
                details={'fng': fng, 'level': 'extreme_greed'}
            )
        return None

    def _check_decision_change(self, alert: Alert, data: Dict) -> Optional[AlertTrigger]:
        """Check for decision changes (WAIT→PREPARE→EXECUTE)"""
        current_decision = data.get('decision', 'WAIT')
        prev_decision = data.get('prev_decision', 'WAIT')
        target_decision = alert.condition.get('to_decision', None)

        if current_decision != prev_decision:
            if target_decision is None or current_decision == target_decision:
                emoji = "🟢" if current_decision == "EXECUTE" else "🟡" if current_decision == "PREPARE" else "🔴"
                return AlertTrigger(
                    alert=alert,
                    trigger_time=datetime.utcnow().isoformat(),
                    trigger_value=current_decision,
                    message=f"{emoji} تغيير القرار!\n{prev_decision} ← {current_decision}",
                    details={'from': prev_decision, 'to': current_decision}
                )
        return None

    def _check_trend_change(self, alert: Alert, data: Dict) -> Optional[AlertTrigger]:
        """Check for trend changes"""
        current_trend = data.get('trend', 'neutral')
        prev_trend = data.get('prev_trend', 'neutral')

        if current_trend != prev_trend:
            trend_ar = {
                'bullish': 'صاعد 📈',
                'bearish': 'هابط 📉',
                'neutral': 'محايد ↔️'
            }
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value=current_trend,
                message=f"🔄 تغيير الاتجاه!\n{trend_ar.get(prev_trend, prev_trend)} ← {trend_ar.get(current_trend, current_trend)}",
                details={'from': prev_trend, 'to': current_trend}
            )
        return None

    def _check_alignment(self, alert: Alert, data: Dict) -> Optional[AlertTrigger]:
        """Check for high alignment score"""
        alignment = data.get('alignment', 0)
        threshold = alert.condition.get('threshold', 3)

        if alignment >= threshold:
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value=alignment,
                message=f"🎯 توافق عالي!\n{alignment}/4 فريمات متوافقة",
                details={'alignment': alignment, 'threshold': threshold}
            )
        return None

    def _check_ai_signal(self, alert: Alert, data: Dict) -> Optional[AlertTrigger]:
        """Check for strong AI signals"""
        ai_score = data.get('ai_score', 0)
        threshold = alert.condition.get('threshold', 50)
        direction = alert.condition.get('direction', 'any')

        if direction == 'buy' and ai_score >= threshold:
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value=ai_score,
                message=f"🤖📈 إشارة AI شراء قوية!\nدرجة: {ai_score:+.0f}",
                details={'ai_score': ai_score}
            )
        elif direction == 'sell' and ai_score <= -threshold:
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value=ai_score,
                message=f"🤖📉 إشارة AI بيع قوية!\nدرجة: {ai_score:+.0f}",
                details={'ai_score': ai_score}
            )
        elif direction == 'any' and abs(ai_score) >= threshold:
            emoji = "📈" if ai_score > 0 else "📉"
            return AlertTrigger(
                alert=alert,
                trigger_time=datetime.utcnow().isoformat(),
                trigger_value=ai_score,
                message=f"🤖{emoji} إشارة AI قوية!\nدرجة: {ai_score:+.0f}",
                details={'ai_score': ai_score}
            )
        return None


class MarketScanner:
    """Periodic market scanner for alerts"""

    def __init__(self, check_interval: int = 60):
        """
        Args:
            check_interval: Seconds between scans
        """
        self.check_interval = check_interval
        self.storage = AlertStorage()
        self.checker = AlertConditionChecker()
        self.running = False
        self.thread = None
        self.callbacks: List[Callable[[AlertTrigger], None]] = []
        self.last_market_state: Dict[str, Dict] = {}

        # Import analyzers lazily
        self._mtf_engine = None
        self._data_manager = None

    def _get_mtf_engine(self, symbol: str):
        """Lazy load MTF engine"""
        from mtf_analyzer import MTFDecisionEngine
        return MTFDecisionEngine(symbol)

    def _get_data_manager(self):
        """Lazy load data manager"""
        if self._data_manager is None:
            from data_providers import create_data_manager
            self._data_manager = create_data_manager()
        return self._data_manager

    def add_callback(self, callback: Callable[[AlertTrigger], None]):
        """Add callback for triggered alerts"""
        self.callbacks.append(callback)

    def remove_callback(self, callback: Callable[[AlertTrigger], None]):
        """Remove callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    def _notify(self, trigger: AlertTrigger):
        """Notify all callbacks"""
        for callback in self.callbacks:
            try:
                callback(trigger)
            except Exception as e:
                print(f"Alert callback error: {e}")

    def get_market_data(self, symbol: str) -> Dict:
        """Get current market data for symbol"""
        try:
            engine = self._get_mtf_engine(symbol)
            result = engine.analyze()

            # Extract relevant data
            data = {
                'symbol': symbol,
                'price': result.m5.price if result.m5 else 0,
                'rsi': result.m15.rsi if result.m15 else 50,
                'ema_20': result.m15.ema_20 if result.m15 else 0,
                'ema_50': result.m15.ema_50 if result.m15 else 0,
                'decision': result.decision.value,
                'alignment': result.alignment_score,
                'trend': result.overall_bias.value if result.overall_bias else 'neutral',
            }

            # Add AI data if available
            if result.ai_analysis:
                data['ai_score'] = result.ai_analysis.ai_score
                data['fear_greed'] = result.ai_analysis.sentiment.fear_greed_index
                data['patterns'] = result.ai_analysis.patterns.patterns_found

            # Track previous values for crossover/change detection
            prev_state = self.last_market_state.get(symbol, {})
            data['prev_ema_20'] = prev_state.get('ema_20', data['ema_20'])
            data['prev_ema_50'] = prev_state.get('ema_50', data['ema_50'])
            data['prev_decision'] = prev_state.get('decision', data['decision'])
            data['prev_trend'] = prev_state.get('trend', data['trend'])

            # Update last state
            self.last_market_state[symbol] = {
                'ema_20': data['ema_20'],
                'ema_50': data['ema_50'],
                'decision': data['decision'],
                'trend': data['trend'],
                'price': data['price'],
            }

            return data

        except Exception as e:
            print(f"Error getting market data for {symbol}: {e}")
            return {}

    def check_alerts(self, symbol: str = None):
        """Check all active alerts"""
        alerts = self.storage.get_active(symbol)
        triggered = []

        # Group alerts by symbol
        symbols = set(a.symbol for a in alerts)

        for sym in symbols:
            market_data = self.get_market_data(sym)
            if not market_data:
                continue

            sym_alerts = [a for a in alerts if a.symbol.upper() == sym.upper()]

            for alert in sym_alerts:
                # Check cooldown for repeating alerts
                if alert.repeat and alert.last_triggered:
                    last = datetime.fromisoformat(alert.last_triggered)
                    cooldown = timedelta(minutes=alert.cooldown_minutes)
                    if datetime.utcnow() - last < cooldown:
                        continue

                # Check alert condition
                trigger = self.checker.check(alert, market_data)

                if trigger:
                    triggered.append(trigger)
                    self._notify(trigger)

                    # Update alert status
                    if alert.repeat:
                        alert.last_triggered = datetime.utcnow().isoformat()
                        self.storage.save()
                    else:
                        self.storage.update_status(alert.id, AlertStatus.TRIGGERED)

        return triggered

    def _scan_loop(self):
        """Main scanning loop"""
        while self.running:
            try:
                self.check_alerts()
            except Exception as e:
                print(f"Scan error: {e}")

            time.sleep(self.check_interval)

    def start(self):
        """Start the scanner in background"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._scan_loop, daemon=True)
            self.thread.start()
            print(f"Scanner started (interval: {self.check_interval}s)")

    def stop(self):
        """Stop the scanner"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
            print("Scanner stopped")


class SmartAlertManager:
    """High-level interface for managing alerts"""

    def __init__(self, scan_interval: int = 300):
        """
        Args:
            scan_interval: Seconds between automatic scans (default 5 minutes)
        """
        self.storage = AlertStorage()
        self.scanner = MarketScanner(check_interval=scan_interval)
        self.checker = AlertConditionChecker()

    def create_price_alert(self, symbol: str, price: float, above: bool = True,
                          repeat: bool = False, user_id: str = None) -> str:
        """Create a price alert"""
        alert_type = AlertType.PRICE_ABOVE if above else AlertType.PRICE_BELOW
        direction = "فوق" if above else "تحت"

        alert = Alert(
            id=self._generate_id(),
            alert_type=alert_type,
            symbol=symbol.upper(),
            condition={'price': price},
            message=f"تنبيه عند وصول {symbol} {direction} {price:,.2f}",
            repeat=repeat,
            user_id=user_id
        )
        return self.storage.add(alert)

    def create_rsi_alert(self, symbol: str, overbought: bool = True,
                        threshold: float = None, repeat: bool = True, user_id: str = None) -> str:
        """Create RSI alert"""
        if overbought:
            alert_type = AlertType.RSI_OVERBOUGHT
            threshold = threshold or 70
            msg = f"تنبيه تشبع شرائي عند RSI > {threshold}"
        else:
            alert_type = AlertType.RSI_OVERSOLD
            threshold = threshold or 30
            msg = f"تنبيه تشبع بيعي عند RSI < {threshold}"

        alert = Alert(
            id=self._generate_id(),
            alert_type=alert_type,
            symbol=symbol.upper(),
            condition={'threshold': threshold},
            message=msg,
            repeat=repeat,
            cooldown_minutes=30,
            user_id=user_id
        )
        return self.storage.add(alert)

    def create_ema_crossover_alert(self, symbol: str, direction: str = 'any',
                                   repeat: bool = True, user_id: str = None) -> str:
        """Create EMA crossover alert"""
        dir_ar = {'bullish': 'صاعد', 'bearish': 'هابط', 'any': 'أي'}

        alert = Alert(
            id=self._generate_id(),
            alert_type=AlertType.EMA_CROSSOVER,
            symbol=symbol.upper(),
            condition={'direction': direction},
            message=f"تنبيه تقاطع EMA20/50 ({dir_ar.get(direction, direction)})",
            repeat=repeat,
            cooldown_minutes=60,
            priority=AlertPriority.HIGH,
            user_id=user_id
        )
        return self.storage.add(alert)

    def create_pattern_alert(self, symbol: str, pattern: str = None,
                            repeat: bool = True, user_id: str = None) -> str:
        """Create pattern detection alert"""
        pattern_desc = pattern or "أي نمط"

        alert = Alert(
            id=self._generate_id(),
            alert_type=AlertType.PATTERN_DETECTED,
            symbol=symbol.upper(),
            condition={'pattern': pattern},
            message=f"تنبيه اكتشاف نمط ({pattern_desc})",
            repeat=repeat,
            cooldown_minutes=60,
            user_id=user_id
        )
        return self.storage.add(alert)

    def create_decision_alert(self, symbol: str, to_decision: str = None,
                             repeat: bool = True, user_id: str = None) -> str:
        """Create decision change alert (WAIT→PREPARE→EXECUTE)"""
        decision_ar = {'EXECUTE': 'تنفيذ', 'PREPARE': 'استعداد', 'WAIT': 'انتظار'}

        alert = Alert(
            id=self._generate_id(),
            alert_type=AlertType.DECISION_CHANGE,
            symbol=symbol.upper(),
            condition={'to_decision': to_decision},
            message=f"تنبيه تغيير القرار إلى {decision_ar.get(to_decision, 'أي')}",
            repeat=repeat,
            cooldown_minutes=15,
            priority=AlertPriority.HIGH if to_decision == 'EXECUTE' else AlertPriority.MEDIUM,
            user_id=user_id
        )
        return self.storage.add(alert)

    def create_ai_signal_alert(self, symbol: str, threshold: float = 50,
                              direction: str = 'any', repeat: bool = True, user_id: str = None) -> str:
        """Create AI signal alert"""
        dir_ar = {'buy': 'شراء', 'sell': 'بيع', 'any': 'أي'}

        alert = Alert(
            id=self._generate_id(),
            alert_type=AlertType.AI_SIGNAL,
            symbol=symbol.upper(),
            condition={'threshold': threshold, 'direction': direction},
            message=f"تنبيه إشارة AI قوية ({dir_ar.get(direction, direction)})",
            repeat=repeat,
            cooldown_minutes=60,
            priority=AlertPriority.HIGH,
            user_id=user_id
        )
        return self.storage.add(alert)

    def create_fear_greed_alert(self, extreme_fear: int = 20, extreme_greed: int = 80,
                               repeat: bool = True, user_id: str = None) -> str:
        """Create Fear & Greed extreme alert"""
        alert = Alert(
            id=self._generate_id(),
            alert_type=AlertType.FEAR_GREED_EXTREME,
            symbol="MARKET",
            condition={'extreme_fear': extreme_fear, 'extreme_greed': extreme_greed},
            message=f"تنبيه مشاعر السوق المتطرفة",
            repeat=repeat,
            cooldown_minutes=240,  # 4 hours
            priority=AlertPriority.MEDIUM,
            user_id=user_id
        )
        return self.storage.add(alert)

    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert"""
        return self.storage.remove(alert_id)

    def get_alerts(self, symbol: str = None, user_id: str = None) -> List[Alert]:
        """Get all active alerts"""
        alerts = self.storage.get_active(symbol)
        if user_id:
            alerts = [a for a in alerts if a.user_id == user_id]
        return alerts

    def format_alerts_list(self, symbol: str = None, user_id: str = None) -> str:
        """Format alerts list for display"""
        alerts = self.get_alerts(symbol, user_id)

        if not alerts:
            return "📭 لا توجد تنبيهات نشطة"

        msg = f"🔔 *التنبيهات النشطة ({len(alerts)})*\n\n"

        type_icons = {
            AlertType.PRICE_ABOVE: "💰⬆️",
            AlertType.PRICE_BELOW: "💰⬇️",
            AlertType.RSI_OVERBOUGHT: "📊🔴",
            AlertType.RSI_OVERSOLD: "📊🟢",
            AlertType.EMA_CROSSOVER: "📈🔄",
            AlertType.PATTERN_DETECTED: "🎯",
            AlertType.DECISION_CHANGE: "⚡",
            AlertType.AI_SIGNAL: "🤖",
            AlertType.FEAR_GREED_EXTREME: "😱",
        }

        for alert in alerts:
            icon = type_icons.get(alert.alert_type, "🔔")
            repeat_icon = "🔁" if alert.repeat else "1️⃣"
            msg += f"{icon} `{alert.id[:8]}` {alert.symbol}\n"
            msg += f"   {alert.message} {repeat_icon}\n\n"

        return msg

    def add_notification_callback(self, callback: Callable[[AlertTrigger], None]):
        """Add callback for alert notifications"""
        self.scanner.add_callback(callback)

    def start_scanner(self):
        """Start background scanner"""
        self.scanner.start()

    def stop_scanner(self):
        """Stop background scanner"""
        self.scanner.stop()

    def check_now(self, symbol: str = None) -> List[AlertTrigger]:
        """Manually check alerts now"""
        return self.scanner.check_alerts(symbol)

    def _generate_id(self) -> str:
        """Generate unique alert ID"""
        data = f"{datetime.utcnow().isoformat()}{os.urandom(8).hex()}"
        return hashlib.md5(data.encode()).hexdigest()[:12]


# Quick setup function
def create_alert_manager(scan_interval: int = 300) -> SmartAlertManager:
    """Create and configure alert manager"""
    return SmartAlertManager(scan_interval)


if __name__ == "__main__":
    # Test the alert system
    print("Testing Smart Alerts System\n")

    manager = create_alert_manager(scan_interval=60)

    # Create some test alerts
    print("Creating test alerts...")

    # Price alert
    price_id = manager.create_price_alert('BTC-USD', 100000, above=True)
    print(f"  Price alert: {price_id}")

    # RSI alert
    rsi_id = manager.create_rsi_alert('BTC-USD', overbought=False, threshold=25)
    print(f"  RSI alert: {rsi_id}")

    # Decision alert
    decision_id = manager.create_decision_alert('BTC-USD', to_decision='EXECUTE')
    print(f"  Decision alert: {decision_id}")

    # AI signal alert
    ai_id = manager.create_ai_signal_alert('BTC-USD', threshold=40, direction='any')
    print(f"  AI signal alert: {ai_id}")

    # List alerts
    print("\n" + manager.format_alerts_list())

    # Test callback
    def on_alert(trigger: AlertTrigger):
        print(f"\n🚨 ALERT TRIGGERED!")
        print(f"   {trigger.message}")

    manager.add_notification_callback(on_alert)

    # Check alerts manually
    print("\nChecking alerts...")
    triggered = manager.check_now('BTC-USD')
    print(f"Triggered: {len(triggered)} alerts")

    for t in triggered:
        print(f"  - {t.message}")
