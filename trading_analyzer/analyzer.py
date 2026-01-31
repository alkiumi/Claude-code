"""
Market Decision Engine
Capital preservation first. Growth second.
"""
import pandas as pd
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from indicators import Indicators


class Decision(Enum):
    WAIT = "WAIT"
    PREPARE = "PREPARE"
    EXECUTE = "EXECUTE"


class Regime(Enum):
    TREND_UP = "Uptrend"
    TREND_DOWN = "Downtrend"
    RANGE = "Range"
    CORRECTION = "Correction"
    UNCLEAR = "Unclear"


class Direction(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Analysis:
    decision: Decision
    direction: Optional[Direction]
    regime: Regime

    # For EXECUTE
    entry_zone: Optional[tuple]  # (low, high)
    stop_loss: Optional[float]
    target: Optional[float]
    risk_reward: Optional[float]
    hold_time: Optional[str]

    # Context
    reasons: List[str]
    missing_conditions: List[str]
    watch_levels: List[str]

    # Raw data
    price: float
    ema_20: float
    ema_50: float
    rsi: float
    atr: float


class DecisionEngine:
    """
    Elite discretionary trader + risk manager.
    Thinks in scenarios, not signals.
    """

    def __init__(self, df: pd.DataFrame, symbol: str):
        self.symbol = symbol
        self.ind = Indicators(df)
        self.data = self.ind.current()
        self.candles = self.ind.recent_candles(10)

    def analyze(self) -> Analysis:
        # Step 1: Determine market regime
        regime = self._assess_regime()

        # Step 2: Evaluate all conditions
        conditions = self._evaluate_conditions(regime)

        # Step 3: Make decision
        decision, direction = self._make_decision(regime, conditions)

        # Step 4: Build trade plan if EXECUTE
        entry_zone, sl, target, rr, hold_time = None, None, None, None, None
        if decision == Decision.EXECUTE and direction:
            entry_zone, sl, target, rr, hold_time = self._build_trade_plan(direction)

        # Step 5: Compile analysis
        return Analysis(
            decision=decision,
            direction=direction,
            regime=regime,
            entry_zone=entry_zone,
            stop_loss=sl,
            target=target,
            risk_reward=rr,
            hold_time=hold_time,
            reasons=conditions['reasons'],
            missing_conditions=conditions['missing'],
            watch_levels=conditions['watch'],
            price=self.data['close'],
            ema_20=self.data['ema_20'],
            ema_50=self.data['ema_50'],
            rsi=self.data['rsi'],
            atr=self.data['atr']
        )

    def _assess_regime(self) -> Regime:
        """Determine market regime from structure"""
        ema_20 = self.data['ema_20']
        ema_50 = self.data['ema_50']
        close = self.data['close']
        slope_20 = self.data['ema_20_slope']
        slope_50 = self.data['ema_50_slope']
        separation = abs(self.data['ema_separation'])
        atr = self.data['atr']

        # EMAs aligned and sloping same direction = trend
        if ema_20 > ema_50 and slope_20 > 0 and slope_50 > 0:
            if separation > atr * 0.5:
                return Regime.TREND_UP
            else:
                return Regime.CORRECTION  # Weak trend

        if ema_20 < ema_50 and slope_20 < 0 and slope_50 < 0:
            if separation > atr * 0.5:
                return Regime.TREND_DOWN
            else:
                return Regime.CORRECTION

        # EMAs flat and close together = range
        if abs(slope_20) < atr * 0.1 and abs(slope_50) < atr * 0.1:
            if separation < atr * 0.3:
                return Regime.RANGE

        # EMAs crossing or conflicting slopes
        if (slope_20 > 0 and slope_50 < 0) or (slope_20 < 0 and slope_50 > 0):
            return Regime.CORRECTION

        return Regime.UNCLEAR

    def _evaluate_conditions(self, regime: Regime) -> dict:
        """Evaluate all 6 decision framework points"""
        close = self.data['close']
        ema_20 = self.data['ema_20']
        ema_50 = self.data['ema_50']
        rsi = self.data['rsi']
        atr = self.data['atr']
        slope_20 = self.data['ema_20_slope']

        reasons = []
        missing = []
        watch = []

        # 1. Market regime
        if regime in [Regime.TREND_UP, Regime.TREND_DOWN]:
            reasons.append(f"Clear {regime.value} regime")
        elif regime == Regime.RANGE:
            missing.append("No clear trend - range bound")
        elif regime == Regime.CORRECTION:
            missing.append("Market in correction phase")
        else:
            missing.append("Regime unclear - no trade")

        # 2. Price location relative to EMAs
        price_vs_ema20 = (close - ema_20) / atr
        price_vs_ema50 = (close - ema_50) / atr

        if regime == Regime.TREND_UP:
            if 0 < price_vs_ema20 < 1.5:
                reasons.append("Price in healthy position above EMA 20")
            elif price_vs_ema20 > 2:
                missing.append("Price overextended from EMA 20")
                watch.append(f"Wait for pullback to {ema_20:.2f}")
            elif price_vs_ema20 < 0:
                watch.append(f"Price below EMA 20 - watch for reclaim at {ema_20:.2f}")

        if regime == Regime.TREND_DOWN:
            if -1.5 < price_vs_ema20 < 0:
                reasons.append("Price in healthy position below EMA 20")
            elif price_vs_ema20 < -2:
                missing.append("Price overextended from EMA 20")
                watch.append(f"Wait for pullback to {ema_20:.2f}")
            elif price_vs_ema20 > 0:
                watch.append(f"Price above EMA 20 - watch for rejection at {ema_20:.2f}")

        # 3. EMA slope and separation
        if abs(slope_20) > atr * 0.2:
            reasons.append("EMA 20 showing strong slope")
        else:
            missing.append("EMA 20 slope weak - momentum lacking")

        # 4. RSI momentum
        rsi_prev = self.data['prev_rsi']
        rsi_direction = rsi - rsi_prev

        if regime == Regime.TREND_UP:
            if 40 < rsi < 70:
                reasons.append(f"RSI ({rsi:.1f}) in bullish zone")
                if rsi_direction > 0:
                    reasons.append("RSI momentum rising")
            elif rsi > 75:
                missing.append(f"RSI ({rsi:.1f}) overheated")
            elif rsi < 40:
                missing.append(f"RSI ({rsi:.1f}) too weak for uptrend")

        if regime == Regime.TREND_DOWN:
            if 30 < rsi < 60:
                reasons.append(f"RSI ({rsi:.1f}) in bearish zone")
                if rsi_direction < 0:
                    reasons.append("RSI momentum falling")
            elif rsi < 25:
                missing.append(f"RSI ({rsi:.1f}) oversold")
            elif rsi > 60:
                missing.append(f"RSI ({rsi:.1f}) too strong for downtrend")

        # 5. Price behavior (recent candles)
        price_behavior = self._analyze_price_behavior()
        if price_behavior['rejection']:
            reasons.append(f"Price rejection at key level")
        if price_behavior['compression']:
            watch.append("Price compressing - breakout imminent")
        if price_behavior['acceptance']:
            reasons.append("Price accepting current level")

        # 6. Risk-reward viability checked in trade plan

        return {
            'reasons': reasons,
            'missing': missing,
            'watch': watch,
            'score': len(reasons) - len(missing)
        }

    def _analyze_price_behavior(self) -> dict:
        """Analyze recent candles for rejection, acceptance, compression"""
        candles = self.candles
        atr = self.data['atr']

        behavior = {
            'rejection': False,
            'acceptance': False,
            'compression': False
        }

        if len(candles) < 3:
            return behavior

        # Check for rejection (long wicks)
        last = candles.iloc[-1]
        body = abs(last['close'] - last['open'])
        upper_wick = last['high'] - max(last['close'], last['open'])
        lower_wick = min(last['close'], last['open']) - last['low']

        if upper_wick > body * 2:
            behavior['rejection'] = True  # Upper rejection
        if lower_wick > body * 2:
            behavior['rejection'] = True  # Lower rejection

        # Check for compression (decreasing ranges)
        ranges = candles['high'] - candles['low']
        if len(ranges) >= 5:
            if ranges.iloc[-1] < ranges.iloc[-5] * 0.6:
                behavior['compression'] = True

        # Check for acceptance (closing near highs/lows consistently)
        recent_closes = candles.tail(3)
        close_positions = (recent_closes['close'] - recent_closes['low']) / (recent_closes['high'] - recent_closes['low'])
        if close_positions.mean() > 0.7 or close_positions.mean() < 0.3:
            behavior['acceptance'] = True

        return behavior

    def _make_decision(self, regime: Regime, conditions: dict) -> tuple:
        """Final decision logic"""
        score = conditions['score']
        reasons = conditions['reasons']
        missing = conditions['missing']

        # Never trade unclear regime
        if regime == Regime.UNCLEAR:
            return Decision.WAIT, None

        # Need clear trend for execution
        if regime not in [Regime.TREND_UP, Regime.TREND_DOWN]:
            if conditions['watch']:
                return Decision.PREPARE, None
            return Decision.WAIT, None

        # Need positive score and no critical missing conditions
        critical_missing = [m for m in missing if 'overextended' in m.lower() or 'overheated' in m.lower() or 'oversold' in m.lower()]

        if critical_missing:
            return Decision.PREPARE, None

        if score >= 3:
            direction = Direction.BUY if regime == Regime.TREND_UP else Direction.SELL
            return Decision.EXECUTE, direction

        if score >= 1:
            return Decision.PREPARE, None

        return Decision.WAIT, None

    def _build_trade_plan(self, direction: Direction) -> tuple:
        """Build concrete trade plan with ATR-based stops"""
        close = self.data['close']
        atr = self.data['atr']
        ema_20 = self.data['ema_20']

        if direction == Direction.BUY:
            # Entry zone: current price to slightly below
            entry_low = close - atr * 0.3
            entry_high = close + atr * 0.2
            entry_zone = (entry_low, entry_high)

            # Stop: below recent structure or 1.5 ATR
            sl = min(ema_20 - atr * 0.5, close - atr * 1.5)

            # Target: minimum 1.5 RR
            risk = close - sl
            target = close + risk * 1.8

            rr = (target - close) / (close - sl)

        else:  # SELL
            entry_low = close - atr * 0.2
            entry_high = close + atr * 0.3
            entry_zone = (entry_low, entry_high)

            sl = max(ema_20 + atr * 0.5, close + atr * 1.5)

            risk = sl - close
            target = close - risk * 1.8

            rr = (close - target) / (sl - close)

        # Validate RR
        if rr < 1.5:
            return None, None, None, None, None

        hold_time = "2-6 hours based on ATR velocity"

        return entry_zone, sl, target, round(rr, 2), hold_time
