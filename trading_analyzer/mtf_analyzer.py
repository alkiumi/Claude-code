"""
Multi-Timeframe Analyzer
6 Stages across H4, H1, M15, M5
"""
import pandas as pd
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict
from indicators import Indicators
from mtf_data import MTFDataFetcher


class Decision(Enum):
    WAIT = "WAIT"
    PREPARE = "PREPARE"
    EXECUTE = "EXECUTE"


class Trend(Enum):
    STRONG_UP = "صاعد قوي"
    UP = "صاعد"
    WEAK_UP = "صاعد ضعيف"
    NEUTRAL = "محايد"
    WEAK_DOWN = "هابط ضعيف"
    DOWN = "هابط"
    STRONG_DOWN = "هابط قوي"


class Direction(Enum):
    BUY = "شراء"
    SELL = "بيع"
    NONE = "لا يوجد"


@dataclass
class TimeframeAnalysis:
    """Analysis for a single timeframe"""
    timeframe: str
    trend: Trend
    price: float
    ema_20: float
    ema_50: float
    rsi: float
    atr: float
    price_vs_ema20: float  # in ATR units
    price_vs_ema50: float
    ema_20_slope: float
    ema_50_slope: float
    bias: Direction
    notes: List[str] = field(default_factory=list)


@dataclass
class StageResult:
    """Result of a single stage"""
    stage_num: int
    name: str
    passed: bool
    summary: str
    h4_status: str
    h1_status: str
    m15_status: str
    m5_status: str
    details: List[str] = field(default_factory=list)


@dataclass
class MTFAnalysis:
    """Complete Multi-Timeframe Analysis"""
    symbol: str
    fetch_time: str

    # Timeframe analyses
    h4: Optional[TimeframeAnalysis]
    h1: Optional[TimeframeAnalysis]
    m15: Optional[TimeframeAnalysis]
    m5: Optional[TimeframeAnalysis]

    # 6 Stages
    stage1_context: StageResult
    stage2_location: StageResult
    stage3_momentum: StageResult
    stage4_behavior: StageResult
    stage5_levels: StageResult
    stage6_risk: StageResult

    # Alignment
    alignment_score: int  # 0-4 (how many TFs agree)
    overall_bias: Direction

    # Final decision
    decision: Decision
    direction: Optional[Direction]

    # Trade plan
    entry_zone: Optional[tuple]
    stop_loss: Optional[float]
    target: Optional[float]
    risk_reward: Optional[float]
    hold_time: Optional[str]


class MTFDecisionEngine:
    """
    Multi-Timeframe Decision Engine
    H4 → Context (الإطار الأكبر)
    H1 → Trend Direction
    M15 → Decision
    M5 → Timing
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.fetcher = MTFDataFetcher()
        self.data = None
        self.tf_analyses = {}

    def analyze(self) -> MTFAnalysis:
        """Run complete MTF analysis"""

        # Step 1: Fetch all timeframes
        self.data = self.fetcher.fetch_mtf_data(self.symbol)

        # Step 2: Analyze each timeframe
        self.tf_analyses = {}
        for tf in ['H4', 'H1', 'M15', 'M5']:
            if self.data[tf] is not None and len(self.data[tf]) >= 20:
                self.tf_analyses[tf] = self._analyze_timeframe(tf, self.data[tf])

        # Step 3: Calculate alignment
        alignment_score, overall_bias = self._calculate_alignment()

        # Step 4: Run 6 stages
        stage1 = self._stage1_context()
        stage2 = self._stage2_location()
        stage3 = self._stage3_momentum()
        stage4 = self._stage4_behavior()
        stage5 = self._stage5_levels()
        stage6 = self._stage6_risk(overall_bias)

        # Step 5: Final decision
        decision, direction = self._make_decision(
            [stage1, stage2, stage3, stage4, stage5, stage6],
            alignment_score,
            overall_bias
        )

        # Step 6: Trade plan
        entry_zone, sl, target, rr, hold_time = None, None, None, None, None
        if decision == Decision.EXECUTE and direction != Direction.NONE:
            entry_zone, sl, target, rr, hold_time = self._build_trade_plan(direction)

        return MTFAnalysis(
            symbol=self.data['symbol'],
            fetch_time=self.data['fetch_time'],
            h4=self.tf_analyses.get('H4'),
            h1=self.tf_analyses.get('H1'),
            m15=self.tf_analyses.get('M15'),
            m5=self.tf_analyses.get('M5'),
            stage1_context=stage1,
            stage2_location=stage2,
            stage3_momentum=stage3,
            stage4_behavior=stage4,
            stage5_levels=stage5,
            stage6_risk=stage6,
            alignment_score=alignment_score,
            overall_bias=overall_bias,
            decision=decision,
            direction=direction if decision == Decision.EXECUTE else None,
            entry_zone=entry_zone,
            stop_loss=sl,
            target=target,
            risk_reward=rr,
            hold_time=hold_time
        )

    def _analyze_timeframe(self, tf: str, df: pd.DataFrame) -> TimeframeAnalysis:
        """Analyze a single timeframe"""
        ind = Indicators(df)
        data = ind.current()

        price = data['close']
        ema_20 = data['ema_20']
        ema_50 = data['ema_50']
        rsi = data['rsi']
        atr = data['atr']
        slope_20 = data['ema_20_slope']
        slope_50 = data['ema_50_slope']

        # Calculate position vs EMAs
        price_vs_ema20 = (price - ema_20) / atr if atr > 0 else 0
        price_vs_ema50 = (price - ema_50) / atr if atr > 0 else 0

        # Determine trend
        trend = self._determine_trend(ema_20, ema_50, slope_20, slope_50, atr, rsi)

        # Determine bias
        bias = Direction.NONE
        if trend in [Trend.STRONG_UP, Trend.UP]:
            bias = Direction.BUY
        elif trend in [Trend.STRONG_DOWN, Trend.DOWN]:
            bias = Direction.SELL

        notes = []
        if abs(price_vs_ema20) > 2:
            notes.append("السعر ممتد من EMA20")
        if rsi > 70:
            notes.append("تشبع شرائي")
        elif rsi < 30:
            notes.append("تشبع بيعي")

        return TimeframeAnalysis(
            timeframe=tf,
            trend=trend,
            price=price,
            ema_20=ema_20,
            ema_50=ema_50,
            rsi=rsi,
            atr=atr,
            price_vs_ema20=price_vs_ema20,
            price_vs_ema50=price_vs_ema50,
            ema_20_slope=slope_20,
            ema_50_slope=slope_50,
            bias=bias,
            notes=notes
        )

    def _determine_trend(self, ema_20, ema_50, slope_20, slope_50, atr, rsi) -> Trend:
        """Determine trend strength"""
        separation = abs(ema_20 - ema_50) / atr if atr > 0 else 0

        if ema_20 > ema_50:
            if slope_20 > 0 and slope_50 > 0:
                if separation > 1 and rsi > 55:
                    return Trend.STRONG_UP
                elif separation > 0.5:
                    return Trend.UP
                else:
                    return Trend.WEAK_UP
            else:
                return Trend.WEAK_UP
        elif ema_20 < ema_50:
            if slope_20 < 0 and slope_50 < 0:
                if separation > 1 and rsi < 45:
                    return Trend.STRONG_DOWN
                elif separation > 0.5:
                    return Trend.DOWN
                else:
                    return Trend.WEAK_DOWN
            else:
                return Trend.WEAK_DOWN
        else:
            return Trend.NEUTRAL

    def _calculate_alignment(self) -> tuple:
        """Calculate timeframe alignment"""
        buy_count = 0
        sell_count = 0

        for tf in ['H4', 'H1', 'M15', 'M5']:
            if tf in self.tf_analyses:
                bias = self.tf_analyses[tf].bias
                if bias == Direction.BUY:
                    buy_count += 1
                elif bias == Direction.SELL:
                    sell_count += 1

        if buy_count >= 3:
            return buy_count, Direction.BUY
        elif sell_count >= 3:
            return sell_count, Direction.SELL
        else:
            return max(buy_count, sell_count), Direction.NONE

    def _get_tf_status(self, tf: str, check_func) -> str:
        """Get status for a timeframe"""
        if tf not in self.tf_analyses:
            return "❓ لا توجد بيانات"
        return check_func(self.tf_analyses[tf])

    def _stage1_context(self) -> StageResult:
        """Stage 1: Market Context from H4 and H1"""
        details = []

        def check_context(tf_data):
            if tf_data.trend in [Trend.STRONG_UP, Trend.UP]:
                return f"✅ {tf_data.trend.value}"
            elif tf_data.trend in [Trend.STRONG_DOWN, Trend.DOWN]:
                return f"✅ {tf_data.trend.value}"
            else:
                return f"⚠️ {tf_data.trend.value}"

        h4_status = self._get_tf_status('H4', check_context)
        h1_status = self._get_tf_status('H1', check_context)
        m15_status = self._get_tf_status('M15', check_context)
        m5_status = self._get_tf_status('M5', check_context)

        # Check H4 and H1 agreement
        passed = False
        if 'H4' in self.tf_analyses and 'H1' in self.tf_analyses:
            h4_bias = self.tf_analyses['H4'].bias
            h1_bias = self.tf_analyses['H1'].bias

            if h4_bias == h1_bias and h4_bias != Direction.NONE:
                passed = True
                details.append(f"✅ H4 و H1 متوافقان: {h4_bias.value}")
            else:
                details.append(f"⚠️ H4 ({h4_bias.value}) و H1 ({h1_bias.value}) غير متوافقين")

        summary = "السياق: " + ("متوافق ✅" if passed else "غير متوافق ⚠️")

        return StageResult(
            stage_num=1,
            name="السياق",
            passed=passed,
            summary=summary,
            h4_status=h4_status,
            h1_status=h1_status,
            m15_status=m15_status,
            m5_status=m5_status,
            details=details
        )

    def _stage2_location(self) -> StageResult:
        """Stage 2: Price Location vs EMAs"""
        details = []

        def check_location(tf_data):
            pos = tf_data.price_vs_ema20
            if -1.5 < pos < 1.5:
                return f"✅ موقع جيد ({pos:.1f} ATR)"
            else:
                return f"⚠️ ممتد ({pos:.1f} ATR)"

        h4_status = self._get_tf_status('H4', check_location)
        h1_status = self._get_tf_status('H1', check_location)
        m15_status = self._get_tf_status('M15', check_location)
        m5_status = self._get_tf_status('M5', check_location)

        # Check M15 location (decision timeframe)
        passed = False
        if 'M15' in self.tf_analyses:
            pos = self.tf_analyses['M15'].price_vs_ema20
            if -2 < pos < 2:
                passed = True
                details.append(f"✅ M15: السعر في موقع مناسب للدخول")
            else:
                details.append(f"⛔ M15: السعر ممتد ({pos:.1f} ATR)")

        summary = "الموقع: " + ("مناسب ✅" if passed else "ممتد ⛔")

        return StageResult(
            stage_num=2,
            name="الموقع",
            passed=passed,
            summary=summary,
            h4_status=h4_status,
            h1_status=h1_status,
            m15_status=m15_status,
            m5_status=m5_status,
            details=details
        )

    def _stage3_momentum(self) -> StageResult:
        """Stage 3: RSI Momentum"""
        details = []

        def check_momentum(tf_data):
            rsi = tf_data.rsi
            if rsi > 70:
                return f"⚠️ تشبع شرائي ({rsi:.0f})"
            elif rsi < 30:
                return f"⚠️ تشبع بيعي ({rsi:.0f})"
            elif rsi > 50:
                return f"✅ زخم إيجابي ({rsi:.0f})"
            else:
                return f"✅ زخم سلبي ({rsi:.0f})"

        h4_status = self._get_tf_status('H4', check_momentum)
        h1_status = self._get_tf_status('H1', check_momentum)
        m15_status = self._get_tf_status('M15', check_momentum)
        m5_status = self._get_tf_status('M5', check_momentum)

        # Check momentum alignment
        passed = False
        if 'H1' in self.tf_analyses and 'M15' in self.tf_analyses:
            h1_rsi = self.tf_analyses['H1'].rsi
            m15_rsi = self.tf_analyses['M15'].rsi

            # Both not in extreme zones
            if 25 < h1_rsi < 75 and 25 < m15_rsi < 75:
                passed = True
                details.append("✅ الزخم في منطقة صحية")
            else:
                if h1_rsi > 75 or m15_rsi > 75:
                    details.append("⚠️ تشبع شرائي - خطر")
                if h1_rsi < 25 or m15_rsi < 25:
                    details.append("⚠️ تشبع بيعي - احتمال ارتداد")

        summary = "الزخم: " + ("صحي ✅" if passed else "متطرف ⚠️")

        return StageResult(
            stage_num=3,
            name="الزخم",
            passed=passed,
            summary=summary,
            h4_status=h4_status,
            h1_status=h1_status,
            m15_status=m15_status,
            m5_status=m5_status,
            details=details
        )

    def _stage4_behavior(self) -> StageResult:
        """Stage 4: Price Behavior Analysis"""
        details = []

        def check_behavior(tf_data):
            if tf_data.notes:
                return f"⚠️ {', '.join(tf_data.notes)}"
            return "✅ سلوك طبيعي"

        h4_status = self._get_tf_status('H4', check_behavior)
        h1_status = self._get_tf_status('H1', check_behavior)
        m15_status = self._get_tf_status('M15', check_behavior)
        m5_status = self._get_tf_status('M5', check_behavior)

        # Analyze M5 for entry timing
        passed = False
        if 'M5' in self.tf_analyses:
            m5 = self.tf_analyses['M5']
            if abs(m5.price_vs_ema20) < 1:
                passed = True
                details.append("✅ M5: السعر قريب من EMA20 - توقيت جيد")
            else:
                details.append(f"⚠️ M5: انتظر اقتراب السعر من EMA20")

        summary = "السلوك: " + ("مناسب ✅" if passed else "انتظر ⚠️")

        return StageResult(
            stage_num=4,
            name="السلوك",
            passed=passed,
            summary=summary,
            h4_status=h4_status,
            h1_status=h1_status,
            m15_status=m15_status,
            m5_status=m5_status,
            details=details
        )

    def _stage5_levels(self) -> StageResult:
        """Stage 5: Support/Resistance Levels"""
        details = []

        if 'H1' not in self.tf_analyses:
            return StageResult(
                stage_num=5,
                name="المستويات",
                passed=False,
                summary="لا توجد بيانات",
                h4_status="❓",
                h1_status="❓",
                m15_status="❓",
                m5_status="❓",
                details=["لا يمكن تحديد المستويات"]
            )

        h1 = self.tf_analyses['H1']

        # Key levels
        levels = {
            'EMA20': h1.ema_20,
            'EMA50': h1.ema_50,
        }

        # Check if price is near a key level
        near_level = False
        for name, level in levels.items():
            distance = abs(h1.price - level) / h1.atr
            if distance < 0.5:
                near_level = True
                details.append(f"✅ السعر قريب من {name} ({level:.2f})")

        passed = near_level
        if not passed:
            details.append("⚠️ السعر في منطقة فارغة")

        def check_levels(tf_data):
            dist = abs(tf_data.price - tf_data.ema_20) / tf_data.atr
            if dist < 0.5:
                return "✅ قرب EMA20"
            elif dist < 1:
                return "⚠️ متوسط"
            else:
                return "⛔ بعيد"

        return StageResult(
            stage_num=5,
            name="المستويات",
            passed=passed,
            summary="المستويات: " + ("قرب مستوى ✅" if passed else "منطقة فارغة ⛔"),
            h4_status=self._get_tf_status('H4', check_levels),
            h1_status=self._get_tf_status('H1', check_levels),
            m15_status=self._get_tf_status('M15', check_levels),
            m5_status=self._get_tf_status('M5', check_levels),
            details=details
        )

    def _stage6_risk(self, bias: Direction) -> StageResult:
        """Stage 6: Risk Management"""
        details = []

        if 'M15' not in self.tf_analyses or bias == Direction.NONE:
            return StageResult(
                stage_num=6,
                name="المخاطرة",
                passed=False,
                summary="لا يمكن حساب المخاطرة",
                h4_status="❓",
                h1_status="❓",
                m15_status="❓",
                m5_status="❓",
                details=["لا يوجد اتجاه محدد"]
            )

        m15 = self.tf_analyses['M15']
        price = m15.price
        atr = m15.atr
        ema_20 = m15.ema_20

        if bias == Direction.BUY:
            stop = min(ema_20 - atr * 0.5, price - atr * 1.5)
            risk = price - stop
            target = price + risk * 2
        else:
            stop = max(ema_20 + atr * 0.5, price + atr * 1.5)
            risk = stop - price
            target = price - risk * 2

        rr = 2.0

        details.append(f"الوقف: {stop:.2f}")
        details.append(f"الهدف: {target:.2f}")
        details.append(f"R:R = 1:{rr}")

        passed = rr >= 1.5

        # Store for trade plan
        self._trade_plan = {
            'entry': price,
            'stop': stop,
            'target': target,
            'rr': rr,
            'atr': atr
        }

        return StageResult(
            stage_num=6,
            name="المخاطرة",
            passed=passed,
            summary=f"المخاطرة: 1:{rr}",
            h4_status="—",
            h1_status="—",
            m15_status=f"ATR: {atr:.2f}",
            m5_status="—",
            details=details
        )

    def _make_decision(self, stages: List[StageResult], alignment: int, bias: Direction) -> tuple:
        """Make final decision"""
        passed_count = sum(1 for s in stages if s.passed)

        # Need alignment >= 3 and at least 5/6 stages passed
        if alignment >= 3 and passed_count >= 5 and bias != Direction.NONE:
            return Decision.EXECUTE, bias

        # Partial conditions met
        if alignment >= 2 and passed_count >= 3:
            return Decision.PREPARE, bias

        return Decision.WAIT, Direction.NONE

    def _build_trade_plan(self, direction: Direction) -> tuple:
        """Build trade plan"""
        if not hasattr(self, '_trade_plan'):
            return None, None, None, None, None

        plan = self._trade_plan
        atr = plan['atr']

        entry_low = plan['entry'] - atr * 0.2
        entry_high = plan['entry'] + atr * 0.2

        return (
            (entry_low, entry_high),
            plan['stop'],
            plan['target'],
            plan['rr'],
            "30 دقيقة - 4 ساعات"
        )


if __name__ == "__main__":
    engine = MTFDecisionEngine('BTC-USD')
    result = engine.analyze()

    print(f"Symbol: {result.symbol}")
    print(f"Time: {result.fetch_time}")
    print(f"Alignment: {result.alignment_score}/4")
    print(f"Bias: {result.overall_bias.value}")
    print(f"Decision: {result.decision.value}")
