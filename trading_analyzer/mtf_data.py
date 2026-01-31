"""
Multi-Timeframe Data Fetcher
Fetches data for H4, H1, M15, M5
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict
import time


class MTFDataFetcher:
    """Multi-Timeframe Data Fetcher"""

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    # Timeframe configurations
    TIMEFRAMES = {
        'H4': {'interval': '1h', 'period': '1mo', 'candles_needed': 50, 'aggregate': 4},
        'H1': {'interval': '1h', 'period': '1mo', 'candles_needed': 200, 'aggregate': 1},
        'M15': {'interval': '15m', 'period': '5d', 'candles_needed': 200, 'aggregate': 1},
        'M5': {'interval': '5m', 'period': '2d', 'candles_needed': 200, 'aggregate': 1},
    }

    MARKETS = {
        'btc': 'BTC-USD',
        'bitcoin': 'BTC-USD',
        'gold': 'GC=F',
        'xauusd': 'GC=F',
        'eurusd': 'EURUSD=X',
        'gbpusd': 'GBPUSD=X',
    }

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.cache = {}

    def resolve_symbol(self, symbol: str) -> str:
        """Resolve symbol alias to actual ticker"""
        return self.MARKETS.get(symbol.lower(), symbol.upper())

    def fetch_single_timeframe(
        self,
        symbol: str,
        interval: str,
        period: str
    ) -> Optional[pd.DataFrame]:
        """Fetch data for a single timeframe"""
        try:
            params = {
                'interval': interval,
                'range': period,
                'includePrePost': 'false',
            }

            url = f"{self.BASE_URL}/{symbol}"
            response = self.session.get(url, params=params, timeout=15)

            if response.status_code != 200:
                return None

            data = response.json()

            if 'chart' not in data or 'result' not in data['chart']:
                return None

            result = data['chart']['result']
            if not result:
                return None

            result = result[0]
            timestamps = result.get('timestamp', [])
            quote = result.get('indicators', {}).get('quote', [{}])[0]

            if not timestamps:
                return None

            df = pd.DataFrame({
                'open': quote.get('open', []),
                'high': quote.get('high', []),
                'low': quote.get('low', []),
                'close': quote.get('close', []),
                'volume': quote.get('volume', [])
            }, index=pd.to_datetime(timestamps, unit='s'))

            df = df.dropna()
            return df

        except Exception as e:
            print(f"Error fetching {symbol} {interval}: {e}")
            return None

    def aggregate_to_h4(self, df_h1: pd.DataFrame) -> pd.DataFrame:
        """Aggregate H1 data to H4"""
        if df_h1 is None or len(df_h1) < 4:
            return None

        df = df_h1.copy()
        df['h4_group'] = df.index.floor('4h')

        agg = df.groupby('h4_group').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })

        return agg

    def fetch_mtf_data(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """Fetch data for all timeframes"""
        resolved = self.resolve_symbol(symbol)
        result = {
            'symbol': resolved,
            'fetch_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'H4': None,
            'H1': None,
            'M15': None,
            'M5': None,
        }

        # Fetch H1 first (used for H4 aggregation)
        tf_config = self.TIMEFRAMES['H1']
        df_h1 = self.fetch_single_timeframe(
            resolved,
            tf_config['interval'],
            tf_config['period']
        )
        result['H1'] = df_h1
        time.sleep(0.3)

        # Aggregate H1 to H4
        if df_h1 is not None:
            result['H4'] = self.aggregate_to_h4(df_h1)

        # Fetch M15
        tf_config = self.TIMEFRAMES['M15']
        result['M15'] = self.fetch_single_timeframe(
            resolved,
            tf_config['interval'],
            tf_config['period']
        )
        time.sleep(0.3)

        # Fetch M5
        tf_config = self.TIMEFRAMES['M5']
        result['M5'] = self.fetch_single_timeframe(
            resolved,
            tf_config['interval'],
            tf_config['period']
        )

        return result

    def get_current_prices(self, symbol: str) -> Dict:
        """Get current price from all timeframes"""
        data = self.fetch_mtf_data(symbol)

        prices = {
            'symbol': data['symbol'],
            'fetch_time': data['fetch_time'],
        }

        for tf in ['H4', 'H1', 'M15', 'M5']:
            if data[tf] is not None and len(data[tf]) > 0:
                prices[tf] = {
                    'close': data[tf]['close'].iloc[-1],
                    'high': data[tf]['high'].iloc[-1],
                    'low': data[tf]['low'].iloc[-1],
                    'candles': len(data[tf])
                }
            else:
                prices[tf] = None

        return prices


if __name__ == "__main__":
    fetcher = MTFDataFetcher()
    data = fetcher.fetch_mtf_data('BTC-USD')

    print(f"Symbol: {data['symbol']}")
    print(f"Fetch Time: {data['fetch_time']}")

    for tf in ['H4', 'H1', 'M15', 'M5']:
        if data[tf] is not None:
            print(f"\n{tf}: {len(data[tf])} candles")
            print(data[tf].tail(3))
