"""
Scalping Engine - Quick Trading System
M5 & M15 Timeframe Focus
Assets: BTC, XAU/USD (Gold), EUR/USD, USOIL

Features:
- Quick momentum detection
- Micro pattern recognition
- Volume spike detection
- RSI reversal signals
- EMA touch entries
- Tight risk management
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from data_providers import create_data_manager, MultiSourceDataManager


class ScalpSignal(Enum):
    STRONG_BUY = "🟢🟢 شراء قوي"
    BUY = "🟢 شراء"
    WEAK_BUY = "🟢⚪ شراء ضعيف"
    NEUTRAL = "⚪ محايد"
    WEAK_SELL = "🔴⚪ بيع ضعيف"
    SELL = "🔴 بيع"
    STRONG_SELL = "🔴🔴 بيع قوي"


class ScalpSetup(Enum):
    EMA_BOUNCE = "ارتداد من EMA"
    RSI_REVERSAL = "انعكاس RSI"
    MOMENTUM_BURST = "انفجار زخم"
    BREAKOUT = "اختراق"
    PULLBACK = "تراجع"
    VOLUME_SPIKE = "ارتفاع حجم"
    MICRO_PATTERN = "نمط صغير"
    NONE = "لا يوجد"


class RiskLevel(Enum):
    LOW = "منخفض"
    MEDIUM = "متوسط"
    HIGH = "عالي"


@dataclass
class ScalpOpportunity:
    """Single scalping opportunity"""
    symbol: str
    signal: ScalpSignal
    setup_type: ScalpSetup
    timeframe: str  # M5 or M15

    # Entry details
    entry_price: float
    stop_loss: float
    take_profit_1: float  # First target (1:1)
    take_profit_2: float  # Second target (1:2)
    take_profit_3: float  # Extended target (1:3)

    # Risk metrics
    risk_pips: float
    reward_pips: float
    risk_reward: float
    risk_percent: float  # Risk as % of entry

    # Confidence & timing
    confidence: float  # 0-100
    urgency: str  # فوري, قريب, انتظار
    valid_for_minutes: int

    # Technical context
    current_price: float
    rsi: float
    ema_20: float
    ema_50: float
    atr: float
    volume_ratio: float  # Current vs average

    # Reasoning
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    fetch_time: str = ""


@dataclass
class ScalpScan:
    """Complete scalp scan result"""
    opportunities: List[ScalpOpportunity]
    best_opportunity: Optional[ScalpOpportunity]
    market_condition: str  # هادئ, نشط, متقلب
    scan_time: str
    symbols_scanned: List[str]


class ScalpingIndicators:
    """Technical indicators optimized for scalping"""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._calculate_all()

    def _calculate_all(self):
        """Calculate all scalping indicators"""
        close = self.df['close']
        high = self.df['high']
        low = self.df['low']
        volume = self.df['volume'] if 'volume' in self.df.columns else pd.Series([1]*len(close))

        # EMAs (fast for scalping)
        self.df['ema_9'] = close.ewm(span=9, adjust=False).mean()
        self.df['ema_20'] = close.ewm(span=20, adjust=False).mean()
        self.df['ema_50'] = close.ewm(span=50, adjust=False).mean()

        # RSI 7 (faster for scalping)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
        rs = gain / loss.replace(0, 0.0001)
        self.df['rsi_7'] = 100 - (100 / (1 + rs))

        # RSI 14 (standard)
        gain14 = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss14 = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs14 = gain14 / loss14.replace(0, 0.0001)
        self.df['rsi_14'] = 100 - (100 / (1 + rs14))

        # Stochastic RSI
        rsi = self.df['rsi_14']
        rsi_min = rsi.rolling(window=14).min()
        rsi_max = rsi.rolling(window=14).max()
        self.df['stoch_rsi'] = (rsi - rsi_min) / (rsi_max - rsi_min + 0.0001) * 100

        # ATR (7 period for scalping)
        tr = pd.concat([
            high - low,
            abs(high - close.shift(1)),
            abs(low - close.shift(1))
        ], axis=1).max(axis=1)
        self.df['atr_7'] = tr.rolling(window=7).mean()
        self.df['atr_14'] = tr.rolling(window=14).mean()

        # Volume analysis
        self.df['volume_sma'] = volume.rolling(window=20).mean()
        self.df['volume_ratio'] = volume / self.df['volume_sma'].replace(0, 1)

        # Momentum
        self.df['momentum_3'] = close.pct_change(3) * 100
        self.df['momentum_5'] = close.pct_change(5) * 100

        # EMA slopes (for trend direction)
        self.df['ema_9_slope'] = (self.df['ema_9'] - self.df['ema_9'].shift(3)) / self.df['atr_7']
        self.df['ema_20_slope'] = (self.df['ema_20'] - self.df['ema_20'].shift(3)) / self.df['atr_7']

        # Price vs EMAs (in ATR units)
        self.df['price_vs_ema9'] = (close - self.df['ema_9']) / self.df['atr_7']
        self.df['price_vs_ema20'] = (close - self.df['ema_20']) / self.df['atr_7']

        # Candle analysis
        self.df['body'] = close - self.df['open']
        self.df['body_pct'] = abs(self.df['body']) / (high - low + 0.0001)
        self.df['upper_wick'] = high - pd.concat([close, self.df['open']], axis=1).max(axis=1)
        self.df['lower_wick'] = pd.concat([close, self.df['open']], axis=1).min(axis=1) - low

        # Bullish/Bearish candle
        self.df['bullish'] = close > self.df['open']

    def current(self) -> Dict:
        """Get current indicator values"""
        latest = self.df.iloc[-1]
        prev = self.df.iloc[-2] if len(self.df) > 1 else latest

        return {
            'close': latest['close'],
            'open': latest['open'],
            'high': latest['high'],
            'low': latest['low'],
            'ema_9': latest['ema_9'],
            'ema_20': latest['ema_20'],
            'ema_50': latest['ema_50'],
            'rsi_7': latest['rsi_7'],
            'rsi_14': latest['rsi_14'],
            'stoch_rsi': latest['stoch_rsi'],
            'atr_7': latest['atr_7'],
            'atr_14': latest['atr_14'],
            'volume_ratio': latest['volume_ratio'],
            'momentum_3': latest['momentum_3'],
            'momentum_5': latest['momentum_5'],
            'ema_9_slope': latest['ema_9_slope'],
            'ema_20_slope': latest['ema_20_slope'],
            'price_vs_ema9': latest['price_vs_ema9'],
            'price_vs_ema20': latest['price_vs_ema20'],
            'bullish': latest['bullish'],
            'body_pct': latest['body_pct'],
            # Previous values
            'prev_rsi_7': prev['rsi_7'],
            'prev_close': prev['close'],
            'prev_bullish': prev['bullish'],
        }


class ScalpingEngine:
    """
    Scalping Analysis Engine
    Focuses on M5 and M15 timeframes for quick trades
    """

    # Supported scalping assets
    SCALP_ASSETS = {
        'BTC': {'symbol': 'BTC-USD', 'name': 'Bitcoin', 'pip': 1, 'spread': 50},
        'GOLD': {'symbol': 'GC=F', 'name': 'الذهب', 'pip': 0.1, 'spread': 0.3},
        'XAUUSD': {'symbol': 'GC=F', 'name': 'الذهب', 'pip': 0.1, 'spread': 0.3},
        'EURUSD': {'symbol': 'EURUSD=X', 'name': 'EUR/USD', 'pip': 0.0001, 'spread': 0.0002},
        'OIL': {'symbol': 'CL=F', 'name': 'النفط', 'pip': 0.01, 'spread': 0.03},
        'USOIL': {'symbol': 'CL=F', 'name': 'النفط', 'pip': 0.01, 'spread': 0.03},
    }

    def __init__(self):
        self.data_manager = create_data_manager()

    def analyze_scalp(self, asset: str, timeframe: str = 'M15') -> Optional[ScalpOpportunity]:
        """
        Analyze single asset for scalping opportunity

        Args:
            asset: BTC, GOLD, EURUSD, OIL
            timeframe: M5 or M15
        """
        asset_upper = asset.upper()
        if asset_upper not in self.SCALP_ASSETS:
            return None

        asset_info = self.SCALP_ASSETS[asset_upper]
        symbol = asset_info['symbol']

        try:
            # Fetch data
            df = self.data_manager.binance.fetch_ohlcv(symbol, timeframe, limit=100)
            if df is None or len(df) < 50:
                df = self.data_manager.yahoo.fetch_ohlcv(symbol, timeframe, limit=100)

            if df is None or len(df) < 50:
                return None

            # Calculate indicators
            ind = ScalpingIndicators(df)
            data = ind.current()

            # Detect setup
            setup, signal, confidence, reasons, warnings = self._detect_setup(data, ind.df)

            if setup == ScalpSetup.NONE:
                return None

            # Calculate trade parameters
            entry, sl, tp1, tp2, tp3 = self._calculate_trade_params(
                data, signal, asset_info
            )

            # Calculate risk metrics
            risk_pips = abs(entry - sl) / asset_info['pip']
            reward_pips = abs(tp1 - entry) / asset_info['pip']
            risk_reward = reward_pips / risk_pips if risk_pips > 0 else 0
            risk_percent = abs(entry - sl) / entry * 100

            # Determine urgency
            urgency = self._determine_urgency(data, setup)

            return ScalpOpportunity(
                symbol=asset_upper,
                signal=signal,
                setup_type=setup,
                timeframe=timeframe,
                entry_price=entry,
                stop_loss=sl,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                risk_pips=risk_pips,
                reward_pips=reward_pips,
                risk_reward=risk_reward,
                risk_percent=risk_percent,
                confidence=confidence,
                urgency=urgency,
                valid_for_minutes=15 if timeframe == 'M15' else 5,
                current_price=data['close'],
                rsi=data['rsi_7'],
                ema_20=data['ema_20'],
                ema_50=data['ema_50'],
                atr=data['atr_7'],
                volume_ratio=data['volume_ratio'],
                reasons=reasons,
                warnings=warnings,
                fetch_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            )

        except Exception as e:
            print(f"Scalp analysis error for {asset}: {e}")
            return None

    def _detect_setup(self, data: Dict, df: pd.DataFrame) -> Tuple[ScalpSetup, ScalpSignal, float, List[str], List[str]]:
        """Detect scalping setup from indicators"""
        reasons = []
        warnings = []
        score = 0  # -100 to +100
        setup = ScalpSetup.NONE

        rsi = data['rsi_7']
        prev_rsi = data['prev_rsi_7']
        price_vs_ema9 = data['price_vs_ema9']
        price_vs_ema20 = data['price_vs_ema20']
        momentum = data['momentum_3']
        volume_ratio = data['volume_ratio']
        ema_slope = data['ema_9_slope']
        bullish = data['bullish']
        stoch_rsi = data['stoch_rsi']

        # ============ BUY SETUPS ============

        # 1. RSI Reversal from Oversold
        if prev_rsi < 25 and rsi > prev_rsi and rsi < 40:
            score += 30
            setup = ScalpSetup.RSI_REVERSAL
            reasons.append(f"انعكاس RSI من {prev_rsi:.0f} إلى {rsi:.0f}")

        # 2. EMA Bounce (price touches EMA20 in uptrend)
        if 0 < price_vs_ema20 < 0.5 and ema_slope > 0.2 and bullish:
            score += 25
            setup = ScalpSetup.EMA_BOUNCE
            reasons.append("ارتداد من EMA20 في اتجاه صاعد")

        # 3. Momentum Burst
        if momentum > 0.5 and volume_ratio > 1.5:
            score += 20
            setup = ScalpSetup.MOMENTUM_BURST
            reasons.append(f"انفجار زخم +{momentum:.2f}% مع حجم عالي")

        # 4. Pullback in Uptrend
        if ema_slope > 0.3 and -1 < price_vs_ema9 < 0 and stoch_rsi < 30:
            score += 25
            setup = ScalpSetup.PULLBACK
            reasons.append("تراجع في اتجاه صاعد - فرصة دخول")

        # 5. Volume Spike with Bullish Candle
        if volume_ratio > 2.0 and bullish and data['body_pct'] > 0.6:
            score += 20
            setup = ScalpSetup.VOLUME_SPIKE
            reasons.append(f"ارتفاع حجم {volume_ratio:.1f}x مع شمعة صاعدة قوية")

        # ============ SELL SETUPS ============

        # 1. RSI Reversal from Overbought
        if prev_rsi > 75 and rsi < prev_rsi and rsi > 60:
            score -= 30
            setup = ScalpSetup.RSI_REVERSAL
            reasons.append(f"انعكاس RSI من {prev_rsi:.0f} إلى {rsi:.0f}")

        # 2. EMA Bounce (price touches EMA20 in downtrend)
        if -0.5 < price_vs_ema20 < 0 and ema_slope < -0.2 and not bullish:
            score -= 25
            setup = ScalpSetup.EMA_BOUNCE
            reasons.append("ارتداد من EMA20 في اتجاه هابط")

        # 3. Negative Momentum Burst
        if momentum < -0.5 and volume_ratio > 1.5:
            score -= 20
            setup = ScalpSetup.MOMENTUM_BURST
            reasons.append(f"انفجار زخم {momentum:.2f}% مع حجم عالي")

        # 4. Pullback in Downtrend
        if ema_slope < -0.3 and 0 < price_vs_ema9 < 1 and stoch_rsi > 70:
            score -= 25
            setup = ScalpSetup.PULLBACK
            reasons.append("تراجع في اتجاه هابط - فرصة بيع")

        # 5. Volume Spike with Bearish Candle
        if volume_ratio > 2.0 and not bullish and data['body_pct'] > 0.6:
            score -= 20
            setup = ScalpSetup.VOLUME_SPIKE
            reasons.append(f"ارتفاع حجم {volume_ratio:.1f}x مع شمعة هابطة قوية")

        # ============ ADDITIONAL FACTORS ============

        # Trend alignment bonus
        if score > 0 and ema_slope > 0:
            score += 10
            reasons.append("الاتجاه العام صاعد ✓")
        elif score < 0 and ema_slope < 0:
            score -= 10
            reasons.append("الاتجاه العام هابط ✓")

        # Warnings
        if 40 < rsi < 60:
            warnings.append("RSI في منطقة محايدة")
        if volume_ratio < 0.7:
            warnings.append("حجم تداول منخفض")
        if abs(price_vs_ema20) > 2:
            warnings.append("السعر بعيد عن EMA - احتمال تصحيح")

        # Determine signal
        if score >= 50:
            signal = ScalpSignal.STRONG_BUY
        elif score >= 30:
            signal = ScalpSignal.BUY
        elif score >= 15:
            signal = ScalpSignal.WEAK_BUY
        elif score <= -50:
            signal = ScalpSignal.STRONG_SELL
        elif score <= -30:
            signal = ScalpSignal.SELL
        elif score <= -15:
            signal = ScalpSignal.WEAK_SELL
        else:
            signal = ScalpSignal.NEUTRAL
            setup = ScalpSetup.NONE

        confidence = min(100, abs(score) * 1.5)

        return setup, signal, confidence, reasons, warnings

    def _calculate_trade_params(self, data: Dict, signal: ScalpSignal,
                                asset_info: Dict) -> Tuple[float, float, float, float, float]:
        """Calculate entry, SL, and TP levels"""
        price = data['close']
        atr = data['atr_7']
        spread = asset_info['spread']

        # For scalping, use tight stops (1-1.5 ATR)
        sl_distance = atr * 1.2

        is_buy = signal in [ScalpSignal.STRONG_BUY, ScalpSignal.BUY, ScalpSignal.WEAK_BUY]

        if is_buy:
            entry = price + spread  # Account for spread
            sl = price - sl_distance
            tp1 = price + sl_distance * 1.0  # 1:1
            tp2 = price + sl_distance * 1.5  # 1:1.5
            tp3 = price + sl_distance * 2.0  # 1:2
        else:
            entry = price - spread
            sl = price + sl_distance
            tp1 = price - sl_distance * 1.0
            tp2 = price - sl_distance * 1.5
            tp3 = price - sl_distance * 2.0

        return entry, sl, tp1, tp2, tp3

    def _determine_urgency(self, data: Dict, setup: ScalpSetup) -> str:
        """Determine how urgent the entry is"""
        momentum = abs(data['momentum_3'])
        volume_ratio = data['volume_ratio']

        if setup in [ScalpSetup.MOMENTUM_BURST, ScalpSetup.VOLUME_SPIKE]:
            return "فوري ⚡"
        elif momentum > 0.3 and volume_ratio > 1.2:
            return "قريب 🔔"
        else:
            return "انتظار ⏳"

    def scan_all_assets(self, timeframe: str = 'M15') -> ScalpScan:
        """Scan all supported assets for scalping opportunities"""
        opportunities = []
        symbols_scanned = []

        for asset_key in ['BTC', 'GOLD', 'EURUSD', 'OIL']:
            symbols_scanned.append(asset_key)
            opp = self.analyze_scalp(asset_key, timeframe)
            if opp and opp.setup_type != ScalpSetup.NONE:
                opportunities.append(opp)

        # Sort by confidence
        opportunities.sort(key=lambda x: x.confidence, reverse=True)

        # Determine market condition
        if len(opportunities) >= 3:
            market_condition = "نشط 🔥"
        elif len(opportunities) >= 1:
            market_condition = "متوسط 📊"
        else:
            market_condition = "هادئ 😴"

        return ScalpScan(
            opportunities=opportunities,
            best_opportunity=opportunities[0] if opportunities else None,
            market_condition=market_condition,
            scan_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            symbols_scanned=symbols_scanned
        )

    def quick_scan(self, account_balance: float = 1000) -> str:
        """Quick scan returning formatted Arabic message with decision"""
        scan = self.scan_all_assets('M15')

        msg = f"⚡ *فحص السكالبينج السريع*\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"حالة السوق: {scan.market_condition}\n"
        msg += f"⏰ {scan.scan_time[:19]}\n\n"

        if not scan.opportunities:
            msg += "📭 لا توجد فرص سكالبينج حالياً\n"
            msg += "_انتظر تغير ظروف السوق_"
            return msg

        msg += f"*الفرص المتاحة ({len(scan.opportunities)}):*\n\n"

        for opp in scan.opportunities[:3]:  # Top 3
            decision = self.get_entry_decision(opp)
            lot_info = self.calculate_lot_size(opp, account_balance)

            msg += f"{'🟢' if 'BUY' in opp.signal.value else '🔴'} *{opp.symbol}* - {opp.signal.value}\n"

            # Clear decision
            if decision['enter_now']:
                msg += f"   📍 *ادخل الآن!* {decision['emoji']}\n"
            else:
                msg += f"   📍 انتظر ~{decision['wait_minutes']} دقيقة ⏳\n"

            msg += f"   💰 ربح متوقع: ${lot_info['profit_tp1']:.2f}\n"
            msg += f"   📊 لوت: {lot_info['lot_size']:.4f}\n"
            msg += f"   الثقة: {opp.confidence:.0f}%\n\n"

        if scan.best_opportunity:
            best = scan.best_opportunity
            best_decision = self.get_entry_decision(best)
            best_lot = self.calculate_lot_size(best, account_balance)

            msg += f"━━━━━━━━━━━━━━━━━━━━\n"
            msg += f"🎯 *أفضل فرصة: {best.symbol}*\n\n"

            # Main Decision
            if best_decision['enter_now']:
                msg += f"```\n"
                msg += f"🚀 ادخل الآن!\n"
                msg += f"```\n"
            else:
                msg += f"```\n"
                msg += f"⏳ انتظر {best_decision['wait_minutes']} دقيقة\n"
                msg += f"السبب: {best_decision['reason']}\n"
                msg += f"```\n"

            msg += f"\n*التفاصيل:*\n"
            msg += f"   الإشارة: {best.signal.value}\n"
            msg += f"   الدخول: `{best.entry_price:.2f}`\n"
            msg += f"   الوقف: `{best.stop_loss:.2f}`\n"
            msg += f"   الهدف1: `{best.take_profit_1:.2f}`\n"
            msg += f"\n*💰 لرأس مال ${account_balance:,.0f}:*\n"
            msg += f"   اللوت: `{best_lot['lot_size']:.4f}`\n"
            msg += f"   الربح: `${best_lot['profit_tp1']:.2f}` - `${best_lot['profit_tp3']:.2f}`\n"

        return msg

    def calculate_lot_size(self, opp: ScalpOpportunity, account_balance: float = 1000,
                           risk_percent: float = 1.0) -> Dict:
        """
        Calculate recommended lot size based on account balance and risk

        Args:
            opp: ScalpOpportunity object
            account_balance: Account balance in USD (default $1000)
            risk_percent: Maximum risk per trade as % (default 1%)

        Returns:
            Dict with lot_size, risk_usd, potential_profit
        """
        # Risk amount in USD
        risk_usd = account_balance * (risk_percent / 100)

        # Get asset info
        asset_info = self.SCALP_ASSETS.get(opp.symbol, {'pip': 1, 'spread': 0})
        pip_value = asset_info['pip']

        # Calculate pip value based on asset
        if opp.symbol in ['BTC']:
            # BTC: 1 lot = 1 BTC, pip value = $1 per pip per BTC
            pip_value_usd = 1.0
            standard_lot = 1.0  # 1 BTC
        elif opp.symbol in ['GOLD', 'XAUUSD']:
            # Gold: 1 lot = 100 oz, pip value ≈ $10 per pip
            pip_value_usd = 10.0
            standard_lot = 1.0  # 100 oz
        elif opp.symbol in ['EURUSD']:
            # Forex: 1 lot = 100,000, pip value = $10 per pip
            pip_value_usd = 10.0
            standard_lot = 1.0  # 100k units
        elif opp.symbol in ['OIL', 'USOIL']:
            # Oil: 1 lot = 1000 barrels, pip value ≈ $10 per pip
            pip_value_usd = 10.0
            standard_lot = 1.0  # 1000 barrels
        else:
            pip_value_usd = 10.0
            standard_lot = 1.0

        # Calculate lot size
        risk_pips = opp.risk_pips
        if risk_pips <= 0:
            risk_pips = 10  # Default fallback

        # Lot size = Risk USD / (Risk Pips * Pip Value)
        lot_size = risk_usd / (risk_pips * pip_value_usd)

        # Round to sensible values
        if opp.symbol == 'BTC':
            lot_size = round(lot_size, 4)  # 0.0001 BTC minimum
            min_lot = 0.001
        elif opp.symbol in ['GOLD', 'XAUUSD']:
            lot_size = round(lot_size, 2)  # 0.01 lot
            min_lot = 0.01
        else:
            lot_size = round(lot_size, 2)  # 0.01 lot
            min_lot = 0.01

        # Ensure minimum lot size
        lot_size = max(lot_size, min_lot)

        # Calculate potential profits
        profit_tp1 = opp.reward_pips * pip_value_usd * lot_size
        profit_tp2 = opp.reward_pips * 1.5 * pip_value_usd * lot_size
        profit_tp3 = opp.reward_pips * 2.0 * pip_value_usd * lot_size

        return {
            'lot_size': lot_size,
            'risk_usd': risk_usd,
            'profit_tp1': profit_tp1,
            'profit_tp2': profit_tp2,
            'profit_tp3': profit_tp3,
            'pip_value_usd': pip_value_usd
        }

    def get_entry_decision(self, opp: ScalpOpportunity) -> Dict:
        """
        Determine clear entry decision: Enter Now or Wait

        Returns:
            Dict with decision, wait_minutes, reason
        """
        # Strong signals with high confidence = Enter Now
        strong_signals = [ScalpSignal.STRONG_BUY, ScalpSignal.STRONG_SELL]
        medium_signals = [ScalpSignal.BUY, ScalpSignal.SELL]

        decision = {
            'enter_now': False,
            'wait_minutes': 0,
            'reason': '',
            'emoji': ''
        }

        # Check urgency
        if opp.urgency == "فوري ⚡":
            decision['enter_now'] = True
            decision['reason'] = "الزخم قوي والحجم مرتفع"
            decision['emoji'] = "⚡"
            decision['wait_minutes'] = 0

        elif opp.urgency == "قريب 🔔":
            if opp.signal in strong_signals and opp.confidence >= 60:
                decision['enter_now'] = True
                decision['reason'] = "إشارة قوية مع ثقة عالية"
                decision['emoji'] = "✅"
                decision['wait_minutes'] = 0
            else:
                decision['enter_now'] = False
                decision['reason'] = "انتظر تأكيد الشمعة التالية"
                decision['emoji'] = "⏳"
                decision['wait_minutes'] = 5 if opp.timeframe == 'M5' else 15

        else:  # "انتظار ⏳"
            decision['enter_now'] = False

            # Calculate wait time based on conditions
            if opp.confidence < 40:
                decision['wait_minutes'] = 30
                decision['reason'] = "الثقة منخفضة - انتظر إشارة أوضح"
            elif opp.volume_ratio < 1.0:
                decision['wait_minutes'] = 15
                decision['reason'] = "الحجم ضعيف - انتظر نشاط أكبر"
            elif 40 < opp.rsi < 60:
                decision['wait_minutes'] = 20
                decision['reason'] = "RSI محايد - انتظر اتجاه واضح"
            else:
                decision['wait_minutes'] = 10
                decision['reason'] = "انتظر تأكيد إضافي"

            decision['emoji'] = "⏳"

        return decision

    def format_opportunity(self, opp: ScalpOpportunity, account_balance: float = 1000) -> str:
        """Format single opportunity as detailed message with actionable advice"""
        is_buy = 'BUY' in opp.signal.value
        direction_icon = "🟢📈" if is_buy else "🔴📉"
        direction_text = "شراء" if is_buy else "بيع"

        # Get entry decision
        decision = self.get_entry_decision(opp)

        # Get lot size calculation
        lot_info = self.calculate_lot_size(opp, account_balance)

        msg = f"{direction_icon} *سكالبينج {opp.symbol}*\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━\n\n"

        # ========== القرار الواضح ==========
        msg += f"*📍 القرار:*\n"
        if decision['enter_now']:
            msg += f"```\n"
            msg += f"🚀 ادخل الآن! {decision['emoji']}\n"
            msg += f"السبب: {decision['reason']}\n"
            msg += f"```\n\n"
        else:
            msg += f"```\n"
            msg += f"⏳ انتظر!\n"
            msg += f"المدة: ~{decision['wait_minutes']} دقيقة\n"
            msg += f"السبب: {decision['reason']}\n"
            msg += f"```\n\n"

        msg += f"*الإشارة:* {opp.signal.value}\n"
        msg += f"*النوع:* {opp.setup_type.value}\n"
        msg += f"*الفريم:* {opp.timeframe}\n"
        msg += f"*الثقة:* {opp.confidence:.0f}%\n\n"

        # ========== اللوت والربح المتوقع ==========
        msg += f"*💰 اللوت والربح المتوقع:*\n"
        msg += f"```\n"
        msg += f"رأس المال:    ${account_balance:,.0f}\n"
        msg += f"اللوت المقترح: {lot_info['lot_size']:.4f}\n"
        msg += f"المخاطرة:      ${lot_info['risk_usd']:.2f} (1%)\n"
        msg += f"─────────────────────\n"
        msg += f"الربح هدف 1:   ${lot_info['profit_tp1']:.2f} ✓\n"
        msg += f"الربح هدف 2:   ${lot_info['profit_tp2']:.2f} ✓✓\n"
        msg += f"الربح هدف 3:   ${lot_info['profit_tp3']:.2f} ✓✓✓\n"
        msg += f"```\n\n"

        msg += f"*🎯 خطة الصفقة ({direction_text}):*\n"
        msg += f"```\n"
        msg += f"الدخول:    {opp.entry_price:.2f}\n"
        msg += f"الوقف:     {opp.stop_loss:.2f}\n"
        msg += f"الهدف 1:   {opp.take_profit_1:.2f} (1:1)\n"
        msg += f"الهدف 2:   {opp.take_profit_2:.2f} (1:1.5)\n"
        msg += f"الهدف 3:   {opp.take_profit_3:.2f} (1:2)\n"
        msg += f"```\n\n"

        msg += f"*📐 المخاطرة:*\n"
        msg += f"• المخاطرة: {opp.risk_pips:.1f} نقطة ({opp.risk_percent:.2f}%)\n"
        msg += f"• العائد: {opp.reward_pips:.1f} نقطة\n"
        msg += f"• النسبة: 1:{opp.risk_reward:.1f}\n\n"

        if opp.reasons:
            msg += f"*✅ الأسباب:*\n"
            for r in opp.reasons:
                msg += f"  • {r}\n"
            msg += "\n"

        if opp.warnings:
            msg += f"*⚠️ تحذيرات:*\n"
            for w in opp.warnings:
                msg += f"  • {w}\n"
            msg += "\n"

        msg += f"━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"⏱️ صالح لمدة: {opp.valid_for_minutes} دقيقة\n"
        msg += f"_⚡ السكالبينج يتطلب سرعة في التنفيذ_"

        return msg


def create_scalping_engine() -> ScalpingEngine:
    """Create scalping engine instance"""
    return ScalpingEngine()


if __name__ == "__main__":
    print("Testing Scalping Engine\n")

    engine = create_scalping_engine()

    # Test single asset
    print("=" * 50)
    print("Testing BTC Scalp Analysis")
    print("=" * 50)

    opp = engine.analyze_scalp('BTC', 'M15')
    if opp:
        print(f"Signal: {opp.signal.value}")
        print(f"Setup: {opp.setup_type.value}")
        print(f"Entry: {opp.entry_price:.2f}")
        print(f"SL: {opp.stop_loss:.2f}")
        print(f"TP1: {opp.take_profit_1:.2f}")
        print(f"Confidence: {opp.confidence:.0f}%")
        print(f"Urgency: {opp.urgency}")
    else:
        print("No scalp opportunity found")

    # Test full scan
    print("\n" + "=" * 50)
    print("Quick Scan All Assets")
    print("=" * 50)
    print(engine.quick_scan())
