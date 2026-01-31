"""
Technical Indicators - Minimal Set
Only: EMA 20, EMA 50, RSI 14, ATR
"""
import pandas as pd
import numpy as np


class Indicators:
    """Core indicators only. No noise."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._calculate()

    def _ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    def _calculate(self):
        close = self.df['close']
        high = self.df['high']
        low = self.df['low']

        # EMA 20 & 50
        self.df['ema_20'] = self._ema(close, 20)
        self.df['ema_50'] = self._ema(close, 50)

        # RSI 14
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.ewm(span=14, adjust=False).mean()
        avg_loss = loss.ewm(span=14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        self.df['rsi'] = 100 - (100 / (1 + rs))

        # ATR 14
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        self.df['atr'] = tr.ewm(span=14, adjust=False).mean()

        # EMA slopes (rate of change over 3 periods)
        self.df['ema_20_slope'] = self.df['ema_20'].diff(3)
        self.df['ema_50_slope'] = self.df['ema_50'].diff(3)

        # EMA separation
        self.df['ema_separation'] = self.df['ema_20'] - self.df['ema_50']

    def get_data(self) -> pd.DataFrame:
        return self.df

    def current(self) -> dict:
        """Get current values"""
        row = self.df.iloc[-1]
        prev = self.df.iloc[-2] if len(self.df) > 1 else row

        return {
            'close': row['close'],
            'high': row['high'],
            'low': row['low'],
            'ema_20': row['ema_20'],
            'ema_50': row['ema_50'],
            'ema_20_slope': row['ema_20_slope'],
            'ema_50_slope': row['ema_50_slope'],
            'ema_separation': row['ema_separation'],
            'rsi': row['rsi'],
            'atr': row['atr'],
            'prev_close': prev['close'],
            'prev_rsi': prev['rsi']
        }

    def recent_candles(self, n: int = 5) -> pd.DataFrame:
        """Get recent candles for price behavior analysis"""
        return self.df.tail(n)
