"""
وحدة جلب بيانات الأسعار من Yahoo Finance
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


class DataFetcher:
    """جلب بيانات الأسعار التاريخية"""

    def __init__(self):
        self.cache = {}

    def fetch_data(
        self,
        symbol: str,
        period: str = "3mo",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        جلب بيانات السعر لرمز معين

        Args:
            symbol: رمز السهم أو العملة (مثل AAPL, BTC-USD)
            period: الفترة الزمنية (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
            interval: الفاصل الزمني (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo)

        Returns:
            DataFrame يحتوي على بيانات OHLCV
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if df.empty:
                print(f"لا توجد بيانات للرمز: {symbol}")
                return None

            # تنظيف البيانات
            df = df.drop(columns=['Dividends', 'Stock Splits'], errors='ignore')
            df.columns = ['open', 'high', 'low', 'close', 'volume']

            self.cache[symbol] = df
            return df

        except Exception as e:
            print(f"خطأ في جلب البيانات: {e}")
            return None

    def fetch_multiple(
        self,
        symbols: list,
        period: str = "3mo",
        interval: str = "1d"
    ) -> dict:
        """جلب بيانات لعدة رموز"""
        results = {}
        for symbol in symbols:
            data = self.fetch_data(symbol, period, interval)
            if data is not None:
                results[symbol] = data
        return results

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """الحصول على آخر سعر"""
        if symbol in self.cache:
            return self.cache[symbol]['close'].iloc[-1]

        data = self.fetch_data(symbol, period="1d", interval="1m")
        if data is not None:
            return data['close'].iloc[-1]
        return None


if __name__ == "__main__":
    # اختبار
    fetcher = DataFetcher()
    data = fetcher.fetch_data("AAPL")
    if data is not None:
        print(data.tail())
