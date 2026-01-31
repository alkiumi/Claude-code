"""
Market Decision Engine
Six Mandatory Decision Stages
Capital preservation first.
"""
import pandas as pd
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from indicators import Indicators


class Decision(Enum):
    WAIT = "WAIT"
    PREPARE = "PREPARE"
    EXECUTE = "EXECUTE"


class Trend(Enum):
    UPTREND = "صاعد"
    DOWNTREND = "هابط"
    CORRECTION = "تصحيح"
    RANGE = "عرضي"
    UNCLEAR = "غير واضح"


class Direction(Enum):
    BUY = "شراء"
    SELL = "بيع"


@dataclass
class StageResult:
    """Result of a single stage"""
    passed: bool
    summary: str
    details: List[str] = field(default_factory=list)


@dataclass
class Analysis:
    """Complete 6-stage analysis"""
    # Stages
    stage1_context: StageResult
    stage2_location: StageResult
    stage3_momentum: StageResult
    stage4_behavior: StageResult
    stage5_technical: StageResult
    stage6_risk: StageResult

    # Final decision
    decision: Decision
    direction: Optional[Direction]

    # Trade plan (if EXECUTE)
    entry_zone: Optional[tuple]
    stop_loss: Optional[float]
    target: Optional[float]
    risk_reward: Optional[float]
    hold_time: Optional[str]

    # Raw data
    price: float
    ema_20: float
    ema_50: float
    rsi: float
    atr: float


class DecisionEngine:
    """
    Six Mandatory Decision Stages.
    If any stage fails → WAIT / NO TRADE.
    """

    def __init__(self, df: pd.DataFrame, symbol: str):
        self.symbol = symbol
        self.ind = Indicators(df)
        self.data = self.ind.current()
        self.df = self.ind.get_data()
        self._direction_bias = None

    def analyze(self) -> Analysis:
        """Execute all 6 stages in strict order"""

        # Stage 1: Market Context
        stage1 = self._stage1_context()
        if not stage1.passed:
            return self._build_result(stage1, None, None, None, None, None, Decision.WAIT)

        # Stage 2: Price Location
        stage2 = self._stage2_location()
        if not stage2.passed:
            return self._build_result(stage1, stage2, None, None, None, None, Decision.WAIT)

        # Stage 3: Momentum
        stage3 = self._stage3_momentum()
        if not stage3.passed:
            return self._build_result(stage1, stage2, stage3, None, None, None, Decision.PREPARE)

        # Stage 4: Price Behavior
        stage4 = self._stage4_behavior()
        if not stage4.passed:
            return self._build_result(stage1, stage2, stage3, stage4, None, None, Decision.PREPARE)

        # Stage 5: Technical Location
        stage5 = self._stage5_technical()
        if not stage5.passed:
            return self._build_result(stage1, stage2, stage3, stage4, stage5, None, Decision.PREPARE)

        # Stage 6: Risk Logic
        stage6 = self._stage6_risk()
        if not stage6.passed:
            return self._build_result(stage1, stage2, stage3, stage4, stage5, stage6, Decision.WAIT)

        # All stages passed → EXECUTE
        return self._build_result(stage1, stage2, stage3, stage4, stage5, stage6, Decision.EXECUTE)

    def _stage1_context(self) -> StageResult:
        """Stage 1: Market Context (Trend)"""
        ema_20 = self.data['ema_20']
        ema_50 = self.data['ema_50']
        slope_20 = self.data['ema_20_slope']
        slope_50 = self.data['ema_50_slope']
        atr = self.data['atr']
        separation = abs(self.data['ema_separation'])

        details = []
        trend = Trend.UNCLEAR

        # Analyze EMA structure
        if ema_20 > ema_50:
            details.append("EMA 20 فوق EMA 50")
            if slope_20 > 0 and slope_50 > 0:
                details.append("كلا المتوسطين يصعدان")
                if separation > atr * 0.5:
                    trend = Trend.UPTREND
                    self._direction_bias = Direction.BUY
                else:
                    trend = Trend.CORRECTION
                    details.append("الفصل ضعيف - تصحيح محتمل")
            else:
                trend = Trend.CORRECTION
                details.append("الميول متضاربة")
        elif ema_20 < ema_50:
            details.append("EMA 20 تحت EMA 50")
            if slope_20 < 0 and slope_50 < 0:
                details.append("كلا المتوسطين يهبطان")
                if separation > atr * 0.5:
                    trend = Trend.DOWNTREND
                    self._direction_bias = Direction.SELL
                else:
                    trend = Trend.CORRECTION
                    details.append("الفصل ضعيف - تصحيح محتمل")
            else:
                trend = Trend.CORRECTION
                details.append("الميول متضاربة")
        else:
            # EMAs very close
            if abs(slope_20) < atr * 0.1 and abs(slope_50) < atr * 0.1:
                trend = Trend.RANGE
                details.append("المتوسطات مسطحة - سوق عرضي")
            else:
                trend = Trend.UNCLEAR

        passed = trend in [Trend.UPTREND, Trend.DOWNTREND]
        summary = f"السياق: {trend.value}"

        if not passed:
            details.append("⛔ السياق غير واضح - لا تداول")

        return StageResult(passed=passed, summary=summary, details=details)

    def _stage2_location(self) -> StageResult:
        """Stage 2: Price Location (EMA Relationship)"""
        close = self.data['close']
        ema_20 = self.data['ema_20']
        ema_50 = self.data['ema_50']
        atr = self.data['atr']

        details = []
        passed = False

        price_vs_ema20 = (close - ema_20) / atr
        price_vs_ema50 = (close - ema_50) / atr

        # Location analysis
        if close > ema_20:
            details.append(f"السعر فوق EMA 20 بـ {price_vs_ema20:.1f} ATR")
        elif close < ema_20:
            details.append(f"السعر تحت EMA 20 بـ {abs(price_vs_ema20):.1f} ATR")
        else:
            details.append("السعر يختبر EMA 20")

        if close > ema_50:
            details.append(f"السعر فوق EMA 50 بـ {price_vs_ema50:.1f} ATR")
        else:
            details.append(f"السعر تحت EMA 50 بـ {abs(price_vs_ema50):.1f} ATR")

        # Check if location supports bias
        if self._direction_bias == Direction.BUY:
            if 0 < price_vs_ema20 < 2:
                passed = True
                details.append("✓ موقع صحي للشراء")
            elif price_vs_ema20 > 2:
                details.append("⛔ السعر ممتد - انتظر تراجع")
            elif price_vs_ema20 < 0:
                details.append("⛔ السعر تحت EMA 20 - لا شراء")

        elif self._direction_bias == Direction.SELL:
            if -2 < price_vs_ema20 < 0:
                passed = True
                details.append("✓ موقع صحي للبيع")
            elif price_vs_ema20 < -2:
                details.append("⛔ السعر ممتد - انتظر ارتداد")
            elif price_vs_ema20 > 0:
                details.append("⛔ السعر فوق EMA 20 - لا بيع")

        summary = "الموقع: " + ("مناسب ✓" if passed else "غير مناسب ⛔")
        return StageResult(passed=passed, summary=summary, details=details)

    def _stage3_momentum(self) -> StageResult:
        """Stage 3: Momentum (RSI Behavior)"""
        rsi = self.data['rsi']
        prev_rsi = self.data['prev_rsi']

        details = []
        passed = False

        rsi_direction = rsi - prev_rsi

        # RSI position
        if rsi > 50:
            details.append(f"RSI ({rsi:.1f}) فوق 50 - زخم إيجابي")
        else:
            details.append(f"RSI ({rsi:.1f}) تحت 50 - زخم سلبي")

        # RSI direction
        if rsi_direction > 0:
            details.append("RSI يرتفع ↑")
        else:
            details.append("RSI يهبط ↓")

        # Check alignment with bias
        if self._direction_bias == Direction.BUY:
            if rsi > 45 and rsi < 75:
                if rsi_direction >= 0:
                    passed = True
                    details.append("✓ الزخم يدعم الشراء")
                else:
                    details.append("⚠ الزخم يضعف")
            elif rsi >= 75:
                details.append("⛔ تشبع شرائي - خطر")
            else:
                details.append("⛔ الزخم ضعيف جداً للشراء")

        elif self._direction_bias == Direction.SELL:
            if rsi < 55 and rsi > 25:
                if rsi_direction <= 0:
                    passed = True
                    details.append("✓ الزخم يدعم البيع")
                else:
                    details.append("⚠ الزخم يقوى")
            elif rsi <= 25:
                details.append("⛔ تشبع بيعي - خطر")
            else:
                details.append("⛔ الزخم قوي جداً للبيع")

        summary = f"الزخم: RSI {rsi:.1f}"
        return StageResult(passed=passed, summary=summary, details=details)

    def _stage4_behavior(self) -> StageResult:
        """Stage 4: Price Behavior (Candles & Structure)"""
        candles = self.df.tail(5)
        atr = self.data['atr']

        details = []
        passed = False

        rejection = False
        acceptance = False
        compression = False
        impulse = False

        # Analyze last candle
        last = candles.iloc[-1]
        body = abs(last['close'] - last['open'])
        upper_wick = last['high'] - max(last['close'], last['open'])
        lower_wick = min(last['close'], last['open']) - last['low']
        candle_range = last['high'] - last['low']

        # Rejection
        if upper_wick > body * 2:
            rejection = True
            details.append("رفض علوي (ذيل طويل للأعلى)")
        if lower_wick > body * 2:
            rejection = True
            details.append("رفض سفلي (ذيل طويل للأسفل)")

        # Impulse vs small candle
        if body > atr * 0.5:
            impulse = True
            details.append("شمعة اندفاعية قوية")
        elif body < atr * 0.2:
            details.append("شمعة صغيرة - تردد")

        # Compression
        ranges = candles['high'] - candles['low']
        if ranges.iloc[-1] < ranges.iloc[0] * 0.6:
            compression = True
            details.append("ضغط سعري - اختراق وشيك")

        # Acceptance (closes near extremes)
        close_position = (last['close'] - last['low']) / candle_range if candle_range > 0 else 0.5
        if close_position > 0.7:
            acceptance = True
            details.append("إغلاق قوي قرب القمة")
        elif close_position < 0.3:
            acceptance = True
            details.append("إغلاق ضعيف قرب القاع")

        # Evaluate for bias
        if self._direction_bias == Direction.BUY:
            if (lower_wick > body * 1.5) or (acceptance and close_position > 0.6) or impulse:
                passed = True
                details.append("✓ سلوك السعر يدعم الشراء")
            else:
                details.append("⚠ سلوك السعر غير مؤكد")

        elif self._direction_bias == Direction.SELL:
            if (upper_wick > body * 1.5) or (acceptance and close_position < 0.4) or impulse:
                passed = True
                details.append("✓ سلوك السعر يدعم البيع")
            else:
                details.append("⚠ سلوك السعر غير مؤكد")

        summary = "السلوك: " + ("مؤكد ✓" if passed else "غير مؤكد ⚠")
        return StageResult(passed=passed, summary=summary, details=details)

    def _stage5_technical(self) -> StageResult:
        """Stage 5: Technical Location (Support/Resistance)"""
        close = self.data['close']
        high = self.data['high']
        low = self.data['low']
        ema_20 = self.data['ema_20']
        ema_50 = self.data['ema_50']
        atr = self.data['atr']

        details = []
        passed = False

        # Find recent highs/lows as S/R
        recent = self.df.tail(20)
        recent_high = recent['high'].max()
        recent_low = recent['low'].min()

        # Check proximity to key levels
        near_ema20 = abs(close - ema_20) < atr * 0.5
        near_ema50 = abs(close - ema_50) < atr * 0.5
        near_high = abs(close - recent_high) < atr * 0.5
        near_low = abs(close - recent_low) < atr * 0.5

        if near_ema20:
            details.append(f"قرب EMA 20 ({ema_20:.2f})")
        if near_ema50:
            details.append(f"قرب EMA 50 ({ema_50:.2f})")
        if near_high:
            details.append(f"قرب مقاومة ({recent_high:.2f})")
        if near_low:
            details.append(f"قرب دعم ({recent_low:.2f})")

        # Evaluate location quality
        if self._direction_bias == Direction.BUY:
            if near_ema20 or near_ema50 or near_low:
                passed = True
                details.append("✓ موقع تقني جيد للشراء")
            else:
                details.append("⛔ في منتصف المدى - لا دخول")

        elif self._direction_bias == Direction.SELL:
            if near_ema20 or near_ema50 or near_high:
                passed = True
                details.append("✓ موقع تقني جيد للبيع")
            else:
                details.append("⛔ في منتصف المدى - لا دخول")

        summary = "الموقع التقني: " + ("جيد ✓" if passed else "ضعيف ⛔")
        return StageResult(passed=passed, summary=summary, details=details)

    def _stage6_risk(self) -> StageResult:
        """Stage 6: Risk Logic (Before Reward)"""
        close = self.data['close']
        atr = self.data['atr']
        ema_20 = self.data['ema_20']

        details = []
        passed = False

        if self._direction_bias == Direction.BUY:
            # Stop below structure
            stop = min(ema_20 - atr * 0.3, close - atr * 1.5)
            risk = close - stop

            # Target minimum 1.5 RR
            target = close + risk * 1.8

            entry_low = close - atr * 0.2
            entry_high = close + atr * 0.1

        else:  # SELL
            stop = max(ema_20 + atr * 0.3, close + atr * 1.5)
            risk = stop - close

            target = close - risk * 1.8

            entry_low = close - atr * 0.1
            entry_high = close + atr * 0.2

        rr = 1.8  # Fixed minimum

        details.append(f"وقف الخسارة: {stop:.2f}")
        details.append(f"المخاطرة: {risk:.2f} ({(risk/close)*100:.2f}%)")
        details.append(f"الهدف: {target:.2f}")
        details.append(f"نسبة المخاطرة:العائد = 1:{rr}")

        # Validate
        if risk < atr * 0.5:
            details.append("⛔ الوقف قريب جداً")
        elif risk > atr * 2.5:
            details.append("⛔ الوقف بعيد جداً")
        elif rr >= 1.5:
            passed = True
            details.append("✓ منطق المخاطرة سليم")

            # Store for final result
            self._entry_zone = (entry_low, entry_high)
            self._stop_loss = stop
            self._target = target
            self._risk_reward = rr

        summary = f"المخاطرة: 1:{rr}"
        return StageResult(passed=passed, summary=summary, details=details)

    def _build_result(self, s1, s2, s3, s4, s5, s6, decision: Decision) -> Analysis:
        """Build final analysis result"""

        # Default empty stages
        empty = StageResult(passed=False, summary="لم يُقيَّم", details=[])

        entry_zone = None
        stop_loss = None
        target = None
        rr = None
        hold_time = None

        if decision == Decision.EXECUTE and hasattr(self, '_entry_zone'):
            entry_zone = self._entry_zone
            stop_loss = self._stop_loss
            target = self._target
            rr = self._risk_reward
            hold_time = "2-6 ساعات"

        return Analysis(
            stage1_context=s1 or empty,
            stage2_location=s2 or empty,
            stage3_momentum=s3 or empty,
            stage4_behavior=s4 or empty,
            stage5_technical=s5 or empty,
            stage6_risk=s6 or empty,
            decision=decision,
            direction=self._direction_bias if decision == Decision.EXECUTE else None,
            entry_zone=entry_zone,
            stop_loss=stop_loss,
            target=target,
            risk_reward=rr,
            hold_time=hold_time,
            price=self.data['close'],
            ema_20=self.data['ema_20'],
            ema_50=self.data['ema_50'],
            rsi=self.data['rsi'],
            atr=self.data['atr']
        )
