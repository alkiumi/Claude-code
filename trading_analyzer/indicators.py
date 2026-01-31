"""
المؤشرات التقنية للتحليل الفني
"""
import pandas as pd
import numpy as np
from typing import Tuple
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator


class TechnicalIndicators:
    """حساب المؤشرات التقنية"""

    def __init__(self, df: pd.DataFrame):
        """
        Args:
            df: DataFrame يحتوي على أعمدة open, high, low, close, volume
        """
        self.df = df.copy()
        self._calculate_all()

    def _calculate_all(self):
        """حساب جميع المؤشرات"""
        self._calculate_moving_averages()
        self._calculate_rsi()
        self._calculate_macd()
        self._calculate_bollinger_bands()
        self._calculate_stochastic()
        self._calculate_atr()
        self._calculate_obv()

    def _calculate_moving_averages(self):
        """حساب المتوسطات المتحركة"""
        # SMA
        self.df['sma_20'] = SMAIndicator(self.df['close'], window=20).sma_indicator()
        self.df['sma_50'] = SMAIndicator(self.df['close'], window=50).sma_indicator()
        self.df['sma_200'] = SMAIndicator(self.df['close'], window=200).sma_indicator()

        # EMA
        self.df['ema_12'] = EMAIndicator(self.df['close'], window=12).ema_indicator()
        self.df['ema_26'] = EMAIndicator(self.df['close'], window=26).ema_indicator()
        self.df['ema_50'] = EMAIndicator(self.df['close'], window=50).ema_indicator()

    def _calculate_rsi(self, period: int = 14):
        """حساب مؤشر القوة النسبية RSI"""
        rsi = RSIIndicator(self.df['close'], window=period)
        self.df['rsi'] = rsi.rsi()

    def _calculate_macd(self):
        """حساب مؤشر MACD"""
        macd = MACD(self.df['close'])
        self.df['macd'] = macd.macd()
        self.df['macd_signal'] = macd.macd_signal()
        self.df['macd_histogram'] = macd.macd_diff()

    def _calculate_bollinger_bands(self, period: int = 20):
        """حساب نطاقات بولينجر"""
        bb = BollingerBands(self.df['close'], window=period)
        self.df['bb_upper'] = bb.bollinger_hband()
        self.df['bb_middle'] = bb.bollinger_mavg()
        self.df['bb_lower'] = bb.bollinger_lband()
        self.df['bb_width'] = bb.bollinger_wband()

    def _calculate_stochastic(self):
        """حساب مؤشر ستوكاستيك"""
        stoch = StochasticOscillator(
            self.df['high'],
            self.df['low'],
            self.df['close']
        )
        self.df['stoch_k'] = stoch.stoch()
        self.df['stoch_d'] = stoch.stoch_signal()

    def _calculate_atr(self, period: int = 14):
        """حساب متوسط المدى الحقيقي ATR"""
        atr = AverageTrueRange(
            self.df['high'],
            self.df['low'],
            self.df['close'],
            window=period
        )
        self.df['atr'] = atr.average_true_range()

    def _calculate_obv(self):
        """حساب حجم التوازن OBV"""
        obv = OnBalanceVolumeIndicator(self.df['close'], self.df['volume'])
        self.df['obv'] = obv.on_balance_volume()

    def get_data(self) -> pd.DataFrame:
        """إرجاع DataFrame مع جميع المؤشرات"""
        return self.df

    def get_latest_values(self) -> dict:
        """الحصول على آخر قيم للمؤشرات"""
        latest = self.df.iloc[-1]
        return {
            'close': latest['close'],
            'rsi': latest['rsi'],
            'macd': latest['macd'],
            'macd_signal': latest['macd_signal'],
            'macd_histogram': latest['macd_histogram'],
            'sma_20': latest['sma_20'],
            'sma_50': latest['sma_50'],
            'ema_12': latest['ema_12'],
            'ema_26': latest['ema_26'],
            'bb_upper': latest['bb_upper'],
            'bb_lower': latest['bb_lower'],
            'stoch_k': latest['stoch_k'],
            'stoch_d': latest['stoch_d'],
            'atr': latest['atr']
        }

    def detect_crossovers(self) -> dict:
        """اكتشاف التقاطعات"""
        df = self.df.tail(5)
        crossovers = {
            'ema_bullish_cross': False,
            'ema_bearish_cross': False,
            'macd_bullish_cross': False,
            'macd_bearish_cross': False,
            'stoch_bullish_cross': False,
            'stoch_bearish_cross': False
        }

        # EMA crossover (12 و 26)
        if len(df) >= 2:
            prev = df.iloc[-2]
            curr = df.iloc[-1]

            # EMA
            if prev['ema_12'] <= prev['ema_26'] and curr['ema_12'] > curr['ema_26']:
                crossovers['ema_bullish_cross'] = True
            elif prev['ema_12'] >= prev['ema_26'] and curr['ema_12'] < curr['ema_26']:
                crossovers['ema_bearish_cross'] = True

            # MACD
            if prev['macd'] <= prev['macd_signal'] and curr['macd'] > curr['macd_signal']:
                crossovers['macd_bullish_cross'] = True
            elif prev['macd'] >= prev['macd_signal'] and curr['macd'] < curr['macd_signal']:
                crossovers['macd_bearish_cross'] = True

            # Stochastic
            if prev['stoch_k'] <= prev['stoch_d'] and curr['stoch_k'] > curr['stoch_d']:
                crossovers['stoch_bullish_cross'] = True
            elif prev['stoch_k'] >= prev['stoch_d'] and curr['stoch_k'] < curr['stoch_d']:
                crossovers['stoch_bearish_cross'] = True

        return crossovers


if __name__ == "__main__":
    # اختبار
    from data_fetcher import DataFetcher
    fetcher = DataFetcher()
    data = fetcher.fetch_data("AAPL")
    if data is not None:
        indicators = TechnicalIndicators(data)
        print(indicators.get_latest_values())
        print(indicators.detect_crossovers())
