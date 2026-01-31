"""
وحدة جلب بيانات الأسعار من Yahoo Finance
(باستخدام requests مباشرة)
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import time


class DataFetcher:
    """جلب بيانات الأسعار التاريخية"""

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    PERIOD_MAP = {
        "1d": 1,
        "5d": 5,
        "1mo": 30,
        "3mo": 90,
        "6mo": 180,
        "1y": 365,
        "2y": 730,
        "5y": 1825,
    }

    def __init__(self):
        self.cache = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

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
            period: الفترة الزمنية (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y)
            interval: الفاصل الزمني (1m, 5m, 15m, 30m, 1h, 1d, 1wk, 1mo)

        Returns:
            DataFrame يحتوي على بيانات OHLCV
        """
        try:
            # حساب التواريخ
            days = self.PERIOD_MAP.get(period, 90)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            params = {
                'period1': int(start_date.timestamp()),
                'period2': int(end_date.timestamp()),
                'interval': interval,
                'includePrePost': 'false',
                'events': 'history'
            }

            url = f"{self.BASE_URL}/{symbol}"
            response = self.session.get(url, params=params, timeout=10)

            if response.status_code != 200:
                print(f"خطأ في جلب البيانات: HTTP {response.status_code}")
                return None

            data = response.json()

            if 'chart' not in data or 'result' not in data['chart']:
                print(f"لا توجد بيانات للرمز: {symbol}")
                return None

            result = data['chart']['result']
            if not result:
                print(f"لا توجد بيانات للرمز: {symbol}")
                return None

            result = result[0]
            timestamps = result.get('timestamp', [])
            quote = result.get('indicators', {}).get('quote', [{}])[0]

            if not timestamps:
                print(f"لا توجد بيانات للرمز: {symbol}")
                return None

            df = pd.DataFrame({
                'open': quote.get('open', []),
                'high': quote.get('high', []),
                'low': quote.get('low', []),
                'close': quote.get('close', []),
                'volume': quote.get('volume', [])
            }, index=pd.to_datetime(timestamps, unit='s'))

            # تنظيف البيانات
            df = df.dropna()

            if df.empty:
                print(f"لا توجد بيانات للرمز: {symbol}")
                return None

            self.cache[symbol] = df
            return df

        except requests.exceptions.Timeout:
            print(f"انتهت مهلة الاتصال للرمز: {symbol}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"خطأ في الاتصال: {e}")
            return None
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
            time.sleep(0.5)  # تأخير لتجنب حظر الطلبات
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
