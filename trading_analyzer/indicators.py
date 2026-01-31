"""
المؤشرات التقنية للتحليل الفني
(محسوبة يدوياً بدون مكتبات خارجية)
"""
import pandas as pd
import numpy as np
from typing import Tuple


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

    def _sma(self, series: pd.Series, period: int) -> pd.Series:
        """حساب المتوسط المتحرك البسيط"""
        return series.rolling(window=period).mean()

    def _ema(self, series: pd.Series, period: int) -> pd.Series:
        """حساب المتوسط المتحرك الأسي"""
        return series.ewm(span=period, adjust=False).mean()

    def _calculate_moving_averages(self):
        """حساب المتوسطات المتحركة"""
        # SMA
        self.df['sma_20'] = self._sma(self.df['close'], 20)
        self.df['sma_50'] = self._sma(self.df['close'], 50)
        self.df['sma_200'] = self._sma(self.df['close'], 200)

        # EMA
        self.df['ema_12'] = self._ema(self.df['close'], 12)
        self.df['ema_26'] = self._ema(self.df['close'], 26)
        self.df['ema_50'] = self._ema(self.df['close'], 50)

    def _calculate_rsi(self, period: int = 14):
        """حساب مؤشر القوة النسبية RSI"""
        delta = self.df['close'].diff()

        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        # تجنب القسمة على صفر
        rs = avg_gain / avg_loss.replace(0, np.nan)
        self.df['rsi'] = 100 - (100 / (1 + rs))

    def _calculate_macd(self):
        """حساب مؤشر MACD"""
        self.df['macd'] = self._ema(self.df['close'], 12) - self._ema(self.df['close'], 26)
        self.df['macd_signal'] = self._ema(self.df['macd'], 9)
        self.df['macd_histogram'] = self.df['macd'] - self.df['macd_signal']

    def _calculate_bollinger_bands(self, period: int = 20, std_dev: float = 2.0):
        """حساب نطاقات بولينجر"""
        self.df['bb_middle'] = self._sma(self.df['close'], period)
        rolling_std = self.df['close'].rolling(window=period).std()

        self.df['bb_upper'] = self.df['bb_middle'] + (rolling_std * std_dev)
        self.df['bb_lower'] = self.df['bb_middle'] - (rolling_std * std_dev)
        self.df['bb_width'] = (self.df['bb_upper'] - self.df['bb_lower']) / self.df['bb_middle']

    def _calculate_stochastic(self, k_period: int = 14, d_period: int = 3):
        """حساب مؤشر ستوكاستيك"""
        low_min = self.df['low'].rolling(window=k_period).min()
        high_max = self.df['high'].rolling(window=k_period).max()

        # تجنب القسمة على صفر
        denominator = high_max - low_min
        denominator = denominator.replace(0, np.nan)

        self.df['stoch_k'] = 100 * (self.df['close'] - low_min) / denominator
        self.df['stoch_d'] = self._sma(self.df['stoch_k'], d_period)

    def _calculate_atr(self, period: int = 14):
        """حساب متوسط المدى الحقيقي ATR"""
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        self.df['atr'] = true_range.rolling(window=period).mean()

    def _calculate_obv(self):
        """حساب حجم التوازن OBV"""
        obv = [0]
        for i in range(1, len(self.df)):
            if self.df['close'].iloc[i] > self.df['close'].iloc[i-1]:
                obv.append(obv[-1] + self.df['volume'].iloc[i])
            elif self.df['close'].iloc[i] < self.df['close'].iloc[i-1]:
                obv.append(obv[-1] - self.df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        self.df['obv'] = obv

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

        if len(df) >= 2:
            prev = df.iloc[-2]
            curr = df.iloc[-1]

            # EMA crossover
            if not pd.isna(prev['ema_12']) and not pd.isna(prev['ema_26']):
                if prev['ema_12'] <= prev['ema_26'] and curr['ema_12'] > curr['ema_26']:
                    crossovers['ema_bullish_cross'] = True
                elif prev['ema_12'] >= prev['ema_26'] and curr['ema_12'] < curr['ema_26']:
                    crossovers['ema_bearish_cross'] = True

            # MACD crossover
            if not pd.isna(prev['macd']) and not pd.isna(prev['macd_signal']):
                if prev['macd'] <= prev['macd_signal'] and curr['macd'] > curr['macd_signal']:
                    crossovers['macd_bullish_cross'] = True
                elif prev['macd'] >= prev['macd_signal'] and curr['macd'] < curr['macd_signal']:
                    crossovers['macd_bearish_cross'] = True

            # Stochastic crossover
            if not pd.isna(prev['stoch_k']) and not pd.isna(prev['stoch_d']):
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
