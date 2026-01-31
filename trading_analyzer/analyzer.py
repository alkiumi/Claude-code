"""
محرك تحليل فرص التداول
"""
import pandas as pd
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from indicators import TechnicalIndicators


class Signal(Enum):
    """إشارات التداول"""
    STRONG_BUY = "شراء قوي"
    BUY = "شراء"
    NEUTRAL = "محايد"
    SELL = "بيع"
    STRONG_SELL = "بيع قوي"


class TrendDirection(Enum):
    """اتجاه السوق"""
    UPTREND = "صاعد"
    DOWNTREND = "هابط"
    SIDEWAYS = "عرضي"


@dataclass
class TradeOpportunity:
    """فرصة تداول"""
    symbol: str
    signal: Signal
    confidence: float  # 0-100
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_reward_ratio: float
    reasons: List[str]
    trend: TrendDirection


class TradingAnalyzer:
    """محلل فرص التداول"""

    def __init__(self, df: pd.DataFrame, symbol: str):
        self.symbol = symbol
        self.indicators = TechnicalIndicators(df)
        self.df = self.indicators.get_data()
        self.latest = self.indicators.get_latest_values()
        self.crossovers = self.indicators.detect_crossovers()

    def analyze(self) -> TradeOpportunity:
        """تحليل شامل وإنتاج فرصة تداول"""
        # تحديد الاتجاه
        trend = self._determine_trend()

        # حساب النقاط لكل مؤشر
        scores = {
            'rsi': self._analyze_rsi(),
            'macd': self._analyze_macd(),
            'ma': self._analyze_moving_averages(),
            'bb': self._analyze_bollinger(),
            'stoch': self._analyze_stochastic(),
            'trend': self._analyze_trend_strength()
        }

        # حساب الإشارة النهائية
        total_score = sum(scores.values())
        signal, confidence = self._calculate_signal(total_score)

        # جمع الأسباب
        reasons = self._collect_reasons(scores)

        # حساب نقاط الدخول والخروج
        entry, sl, tp1, tp2, tp3 = self._calculate_levels(signal)

        # حساب نسبة المخاطرة للعائد
        risk = abs(entry - sl)
        reward = abs(tp1 - entry)
        rr_ratio = reward / risk if risk > 0 else 0

        return TradeOpportunity(
            symbol=self.symbol,
            signal=signal,
            confidence=confidence,
            entry_price=entry,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            risk_reward_ratio=rr_ratio,
            reasons=reasons,
            trend=trend
        )

    def _determine_trend(self) -> TrendDirection:
        """تحديد اتجاه السوق"""
        close = self.latest['close']
        sma_20 = self.latest['sma_20']
        sma_50 = self.latest['sma_50']

        if pd.isna(sma_50):
            if close > sma_20:
                return TrendDirection.UPTREND
            else:
                return TrendDirection.DOWNTREND

        if close > sma_20 > sma_50:
            return TrendDirection.UPTREND
        elif close < sma_20 < sma_50:
            return TrendDirection.DOWNTREND
        else:
            return TrendDirection.SIDEWAYS

    def _analyze_rsi(self) -> float:
        """تحليل RSI - نطاق من -2 إلى +2"""
        rsi = self.latest['rsi']
        if pd.isna(rsi):
            return 0

        if rsi < 30:
            return 2  # oversold - إشارة شراء
        elif rsi < 40:
            return 1
        elif rsi > 70:
            return -2  # overbought - إشارة بيع
        elif rsi > 60:
            return -1
        return 0

    def _analyze_macd(self) -> float:
        """تحليل MACD - نطاق من -2 إلى +2"""
        score = 0
        histogram = self.latest['macd_histogram']

        if pd.isna(histogram):
            return 0

        # اتجاه الهيستوجرام
        if histogram > 0:
            score += 1
        else:
            score -= 1

        # التقاطعات
        if self.crossovers['macd_bullish_cross']:
            score += 1
        elif self.crossovers['macd_bearish_cross']:
            score -= 1

        return max(-2, min(2, score))

    def _analyze_moving_averages(self) -> float:
        """تحليل المتوسطات المتحركة - نطاق من -2 إلى +2"""
        score = 0
        close = self.latest['close']
        ema_12 = self.latest['ema_12']
        ema_26 = self.latest['ema_26']
        sma_50 = self.latest['sma_50']

        # السعر فوق/تحت EMAs
        if not pd.isna(ema_12):
            if close > ema_12:
                score += 0.5
            else:
                score -= 0.5

        if not pd.isna(ema_26):
            if close > ema_26:
                score += 0.5
            else:
                score -= 0.5

        # ترتيب EMAs
        if not pd.isna(ema_12) and not pd.isna(ema_26):
            if ema_12 > ema_26:
                score += 0.5
            else:
                score -= 0.5

        # التقاطعات
        if self.crossovers['ema_bullish_cross']:
            score += 0.5
        elif self.crossovers['ema_bearish_cross']:
            score -= 0.5

        return max(-2, min(2, score))

    def _analyze_bollinger(self) -> float:
        """تحليل نطاقات بولينجر - نطاق من -2 إلى +2"""
        close = self.latest['close']
        bb_upper = self.latest['bb_upper']
        bb_lower = self.latest['bb_lower']

        if pd.isna(bb_upper) or pd.isna(bb_lower):
            return 0

        bb_range = bb_upper - bb_lower
        position = (close - bb_lower) / bb_range if bb_range > 0 else 0.5

        if position < 0.1:
            return 2  # قرب الحد السفلي - فرصة شراء
        elif position < 0.3:
            return 1
        elif position > 0.9:
            return -2  # قرب الحد العلوي - فرصة بيع
        elif position > 0.7:
            return -1
        return 0

    def _analyze_stochastic(self) -> float:
        """تحليل ستوكاستيك - نطاق من -2 إلى +2"""
        stoch_k = self.latest['stoch_k']
        score = 0

        if pd.isna(stoch_k):
            return 0

        if stoch_k < 20:
            score += 1.5
        elif stoch_k < 30:
            score += 0.5
        elif stoch_k > 80:
            score -= 1.5
        elif stoch_k > 70:
            score -= 0.5

        if self.crossovers['stoch_bullish_cross']:
            score += 0.5
        elif self.crossovers['stoch_bearish_cross']:
            score -= 0.5

        return max(-2, min(2, score))

    def _analyze_trend_strength(self) -> float:
        """تحليل قوة الاتجاه"""
        trend = self._determine_trend()
        if trend == TrendDirection.UPTREND:
            return 1
        elif trend == TrendDirection.DOWNTREND:
            return -1
        return 0

    def _calculate_signal(self, total_score: float) -> tuple:
        """حساب الإشارة النهائية ودرجة الثقة"""
        # المجموع الأقصى هو ±11 تقريباً
        if total_score >= 6:
            return Signal.STRONG_BUY, min(95, 60 + total_score * 3)
        elif total_score >= 3:
            return Signal.BUY, min(80, 50 + total_score * 4)
        elif total_score <= -6:
            return Signal.STRONG_SELL, min(95, 60 + abs(total_score) * 3)
        elif total_score <= -3:
            return Signal.SELL, min(80, 50 + abs(total_score) * 4)
        else:
            return Signal.NEUTRAL, 50 - abs(total_score) * 5

    def _calculate_levels(self, signal: Signal) -> tuple:
        """حساب مستويات الدخول والخروج"""
        close = self.latest['close']
        atr = self.latest['atr']

        if pd.isna(atr):
            atr = close * 0.02  # 2% كقيمة افتراضية

        if signal in [Signal.STRONG_BUY, Signal.BUY]:
            entry = close
            stop_loss = close - (atr * 1.5)
            tp1 = close + (atr * 1.5)
            tp2 = close + (atr * 2.5)
            tp3 = close + (atr * 4)
        elif signal in [Signal.STRONG_SELL, Signal.SELL]:
            entry = close
            stop_loss = close + (atr * 1.5)
            tp1 = close - (atr * 1.5)
            tp2 = close - (atr * 2.5)
            tp3 = close - (atr * 4)
        else:
            entry = close
            stop_loss = close - (atr * 1)
            tp1 = close + (atr * 1)
            tp2 = close + (atr * 1.5)
            tp3 = close + (atr * 2)

        return entry, stop_loss, tp1, tp2, tp3

    def _collect_reasons(self, scores: dict) -> List[str]:
        """جمع أسباب التوصية"""
        reasons = []
        rsi = self.latest['rsi']
        stoch_k = self.latest['stoch_k']

        if scores['rsi'] >= 1.5:
            reasons.append(f"RSI في منطقة التشبع البيعي ({rsi:.1f})")
        elif scores['rsi'] <= -1.5:
            reasons.append(f"RSI في منطقة التشبع الشرائي ({rsi:.1f})")

        if self.crossovers['macd_bullish_cross']:
            reasons.append("تقاطع صعودي لـ MACD")
        elif self.crossovers['macd_bearish_cross']:
            reasons.append("تقاطع هبوطي لـ MACD")

        if self.crossovers['ema_bullish_cross']:
            reasons.append("تقاطع صعودي للمتوسطات المتحركة")
        elif self.crossovers['ema_bearish_cross']:
            reasons.append("تقاطع هبوطي للمتوسطات المتحركة")

        if scores['bb'] >= 1.5:
            reasons.append("السعر قرب الحد السفلي لبولينجر")
        elif scores['bb'] <= -1.5:
            reasons.append("السعر قرب الحد العلوي لبولينجر")

        if scores['stoch'] >= 1:
            reasons.append(f"ستوكاستيك في منطقة التشبع البيعي ({stoch_k:.1f})")
        elif scores['stoch'] <= -1:
            reasons.append(f"ستوكاستيك في منطقة التشبع الشرائي ({stoch_k:.1f})")

        trend = self._determine_trend()
        reasons.append(f"الاتجاه العام: {trend.value}")

        return reasons


if __name__ == "__main__":
    from data_fetcher import DataFetcher
    fetcher = DataFetcher()
    data = fetcher.fetch_data("AAPL")
    if data is not None:
        analyzer = TradingAnalyzer(data, "AAPL")
        opportunity = analyzer.analyze()
        print(f"الإشارة: {opportunity.signal.value}")
        print(f"الثقة: {opportunity.confidence:.1f}%")
        print(f"نقطة الدخول: {opportunity.entry_price:.2f}")
        print(f"وقف الخسارة: {opportunity.stop_loss:.2f}")
        print(f"الهدف الأول: {opportunity.take_profit_1:.2f}")
