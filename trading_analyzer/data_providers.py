"""
Multi-Source Data Providers
- Binance API (Crypto - Real-time)
- Alpha Vantage (Forex)
- Yahoo Finance (Fallback)
- TradingView Webhooks
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from abc import ABC, abstractmethod
from enum import Enum
import time
import json


class DataSource(Enum):
    BINANCE = "binance"
    ALPHA_VANTAGE = "alphavantage"
    YAHOO = "yahoo"
    TRADINGVIEW = "tradingview"


class AssetType(Enum):
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"
    STOCK = "stock"


class BaseDataProvider(ABC):
    """Base class for all data providers"""

    def __init__(self):
        self.session = requests.Session()
        self.last_fetch_time = None
        self.rate_limit_delay = 0.2  # seconds between requests

    @abstractmethod
    def fetch_ohlcv(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data"""
        pass

    @abstractmethod
    def get_supported_intervals(self) -> List[str]:
        """Return list of supported intervals"""
        pass

    def _respect_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        if self.last_fetch_time:
            elapsed = time.time() - self.last_fetch_time
            if elapsed < self.rate_limit_delay:
                time.sleep(self.rate_limit_delay - elapsed)
        self.last_fetch_time = time.time()


class BinanceProvider(BaseDataProvider):
    """
    Binance API - Real-time crypto data
    Free, no API key required for public endpoints
    Rate limit: 1200 requests/minute
    """

    # Try multiple endpoints (some regions block api.binance.com)
    BASE_URLS = [
        "https://api.binance.com/api/v3",
        "https://api1.binance.com/api/v3",
        "https://api2.binance.com/api/v3",
        "https://api3.binance.com/api/v3",
        "https://data-api.binance.vision/api/v3",  # Data API (no geo-restrictions)
    ]
    BASE_URL = "https://data-api.binance.vision/api/v3"  # Default to data API

    # Map our intervals to Binance intervals
    INTERVAL_MAP = {
        'M1': '1m',
        'M5': '5m',
        'M15': '15m',
        'M30': '30m',
        'H1': '1h',
        'H4': '4h',
        'D1': '1d',
        'W1': '1w',
    }

    # Symbol mappings
    SYMBOL_MAP = {
        'BTC-USD': 'BTCUSDT',
        'BTCUSD': 'BTCUSDT',
        'ETH-USD': 'ETHUSDT',
        'ETHUSD': 'ETHUSDT',
        'BNB-USD': 'BNBUSDT',
        'XRP-USD': 'XRPUSDT',
        'SOL-USD': 'SOLUSDT',
        'ADA-USD': 'ADAUSDT',
        'DOGE-USD': 'DOGEUSDT',
    }

    def __init__(self):
        super().__init__()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })

    def resolve_symbol(self, symbol: str) -> str:
        """Convert symbol to Binance format"""
        symbol = symbol.upper().replace('/', '')
        return self.SYMBOL_MAP.get(symbol, symbol)

    def get_supported_intervals(self) -> List[str]:
        return list(self.INTERVAL_MAP.keys())

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int = 200
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data from Binance

        Args:
            symbol: Trading pair (e.g., 'BTC-USD', 'BTCUSDT')
            interval: Timeframe (M1, M5, M15, H1, H4, D1)
            limit: Number of candles (max 1000)

        Returns:
            DataFrame with columns: open, high, low, close, volume
        """
        try:
            self._respect_rate_limit()

            binance_symbol = self.resolve_symbol(symbol)
            binance_interval = self.INTERVAL_MAP.get(interval, interval.lower())

            url = f"{self.BASE_URL}/klines"
            params = {
                'symbol': binance_symbol,
                'interval': binance_interval,
                'limit': min(limit, 1000)
            }

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code != 200:
                print(f"Binance API error: {response.status_code}")
                return None

            data = response.json()

            if not data:
                return None

            # Binance klines format:
            # [open_time, open, high, low, close, volume, close_time, ...]
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            # Convert to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            # Keep only OHLCV
            df = df[['open', 'high', 'low', 'close', 'volume']]

            return df

        except Exception as e:
            print(f"Binance fetch error: {e}")
            return None

    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """Get current price"""
        try:
            self._respect_rate_limit()
            binance_symbol = self.resolve_symbol(symbol)

            url = f"{self.BASE_URL}/ticker/price"
            params = {'symbol': binance_symbol}

            response = self.session.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                return float(data['price'])
            return None

        except Exception:
            return None

    def is_crypto_symbol(self, symbol: str) -> bool:
        """Check if symbol is supported by Binance"""
        crypto_keywords = ['BTC', 'ETH', 'BNB', 'XRP', 'SOL', 'ADA', 'DOGE',
                          'USDT', 'USDC', 'AVAX', 'DOT', 'MATIC', 'LINK']
        symbol_upper = symbol.upper()
        return any(kw in symbol_upper for kw in crypto_keywords)


class AlphaVantageProvider(BaseDataProvider):
    """
    Alpha Vantage API - Forex and Stock data
    Free tier: 25 requests/day
    Premium: Higher limits
    """

    BASE_URL = "https://www.alphavantage.co/query"

    INTERVAL_MAP = {
        'M1': '1min',
        'M5': '5min',
        'M15': '15min',
        'M30': '30min',
        'H1': '60min',
    }

    # Forex symbols
    FOREX_PAIRS = {
        'EURUSD': ('EUR', 'USD'),
        'EURUSD=X': ('EUR', 'USD'),
        'GBPUSD': ('GBP', 'USD'),
        'GBPUSD=X': ('GBP', 'USD'),
        'USDJPY': ('USD', 'JPY'),
        'USDJPY=X': ('USD', 'JPY'),
        'AUDUSD': ('AUD', 'USD'),
        'USDCAD': ('USD', 'CAD'),
        'USDCHF': ('USD', 'CHF'),
    }

    def __init__(self, api_key: str = None):
        super().__init__()
        # Free demo key (limited to 25 requests/day)
        self.api_key = api_key or "demo"
        self.rate_limit_delay = 12  # 5 requests per minute for free tier

    def get_supported_intervals(self) -> List[str]:
        return list(self.INTERVAL_MAP.keys())

    def is_forex_symbol(self, symbol: str) -> bool:
        """Check if symbol is a forex pair"""
        symbol_clean = symbol.upper().replace('=X', '').replace('/', '')
        return symbol_clean in self.FOREX_PAIRS or len(symbol_clean) == 6

    def parse_forex_symbol(self, symbol: str) -> Tuple[str, str]:
        """Parse forex symbol into from/to currencies"""
        symbol_clean = symbol.upper().replace('=X', '').replace('/', '')

        if symbol_clean in self.FOREX_PAIRS:
            return self.FOREX_PAIRS[symbol_clean]

        # Assume first 3 chars are from_currency
        if len(symbol_clean) == 6:
            return symbol_clean[:3], symbol_clean[3:]

        return None, None

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int = 200
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data from Alpha Vantage
        """
        try:
            self._respect_rate_limit()

            from_currency, to_currency = self.parse_forex_symbol(symbol)

            if not from_currency:
                print(f"Invalid forex symbol: {symbol}")
                return None

            av_interval = self.INTERVAL_MAP.get(interval)

            if not av_interval:
                # Use daily for larger timeframes
                params = {
                    'function': 'FX_DAILY',
                    'from_symbol': from_currency,
                    'to_symbol': to_currency,
                    'apikey': self.api_key,
                    'outputsize': 'compact' if limit <= 100 else 'full'
                }
                time_series_key = 'Time Series FX (Daily)'
            else:
                params = {
                    'function': 'FX_INTRADAY',
                    'from_symbol': from_currency,
                    'to_symbol': to_currency,
                    'interval': av_interval,
                    'apikey': self.api_key,
                    'outputsize': 'compact' if limit <= 100 else 'full'
                }
                time_series_key = f'Time Series FX (Intraday)'

            response = self.session.get(self.BASE_URL, params=params, timeout=15)

            if response.status_code != 200:
                return None

            data = response.json()

            # Check for errors
            if 'Error Message' in data:
                print(f"Alpha Vantage error: {data['Error Message']}")
                return None

            if 'Note' in data:
                print(f"Alpha Vantage rate limit: {data['Note']}")
                return None

            # Find the time series key
            ts_key = None
            for key in data.keys():
                if 'Time Series' in key:
                    ts_key = key
                    break

            if not ts_key or ts_key not in data:
                return None

            time_series = data[ts_key]

            records = []
            for timestamp, values in time_series.items():
                records.append({
                    'timestamp': timestamp,
                    'open': float(values.get('1. open', 0)),
                    'high': float(values.get('2. high', 0)),
                    'low': float(values.get('3. low', 0)),
                    'close': float(values.get('4. close', 0)),
                    'volume': 0  # Forex doesn't have volume
                })

            df = pd.DataFrame(records)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)

            return df.tail(limit)

        except Exception as e:
            print(f"Alpha Vantage fetch error: {e}")
            return None


class YahooProvider(BaseDataProvider):
    """
    Yahoo Finance - Fallback provider
    Free, no API key required
    """

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    INTERVAL_MAP = {
        'M1': '1m',
        'M5': '5m',
        'M15': '15m',
        'M30': '30m',
        'H1': '1h',
        'H4': '1h',  # Will aggregate
        'D1': '1d',
        'W1': '1wk',
    }

    PERIOD_MAP = {
        'M1': '1d',
        'M5': '5d',
        'M15': '5d',
        'M30': '1mo',
        'H1': '1mo',
        'H4': '1mo',
        'D1': '1y',
        'W1': '2y',
    }

    def __init__(self):
        super().__init__()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_supported_intervals(self) -> List[str]:
        return list(self.INTERVAL_MAP.keys())

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int = 200
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from Yahoo Finance"""
        try:
            self._respect_rate_limit()

            yahoo_interval = self.INTERVAL_MAP.get(interval, '1h')
            period = self.PERIOD_MAP.get(interval, '1mo')

            url = f"{self.BASE_URL}/{symbol}"
            params = {
                'interval': yahoo_interval,
                'range': period,
                'includePrePost': 'false',
            }

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

            # Aggregate to H4 if needed
            if interval == 'H4' and len(df) >= 4:
                df = self._aggregate_to_h4(df)

            return df.tail(limit)

        except Exception as e:
            print(f"Yahoo fetch error: {e}")
            return None

    def _aggregate_to_h4(self, df_h1: pd.DataFrame) -> pd.DataFrame:
        """Aggregate H1 data to H4"""
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


class TradingViewWebhook:
    """
    TradingView Webhook Handler
    Receives alerts from TradingView
    """

    def __init__(self):
        self.alerts = []
        self.max_alerts = 100

    def parse_alert(self, webhook_data: dict) -> dict:
        """Parse TradingView webhook data"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'symbol': webhook_data.get('symbol', ''),
            'exchange': webhook_data.get('exchange', ''),
            'price': float(webhook_data.get('price', 0)),
            'action': webhook_data.get('action', ''),  # BUY, SELL, ALERT
            'timeframe': webhook_data.get('timeframe', ''),
            'indicator': webhook_data.get('indicator', ''),
            'message': webhook_data.get('message', ''),
        }

    def add_alert(self, webhook_data: dict):
        """Add a new alert"""
        alert = self.parse_alert(webhook_data)
        self.alerts.insert(0, alert)

        # Keep only recent alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[:self.max_alerts]

        return alert

    def get_recent_alerts(self, symbol: str = None, limit: int = 10) -> List[dict]:
        """Get recent alerts, optionally filtered by symbol"""
        alerts = self.alerts

        if symbol:
            alerts = [a for a in alerts if symbol.upper() in a['symbol'].upper()]

        return alerts[:limit]


class MultiSourceDataManager:
    """
    Manages multiple data sources with automatic fallback
    Selects the best source based on asset type
    """

    def __init__(self, alpha_vantage_key: str = None):
        self.binance = BinanceProvider()
        self.alpha_vantage = AlphaVantageProvider(alpha_vantage_key)
        self.yahoo = YahooProvider()
        self.tradingview = TradingViewWebhook()

        self.fetch_log = []

    def detect_asset_type(self, symbol: str) -> AssetType:
        """Detect the type of asset from symbol"""
        symbol_upper = symbol.upper()

        # Crypto
        if self.binance.is_crypto_symbol(symbol):
            return AssetType.CRYPTO

        # Forex
        if self.alpha_vantage.is_forex_symbol(symbol):
            return AssetType.FOREX

        # Gold/Commodities
        if 'GC=F' in symbol or 'GOLD' in symbol_upper or 'XAU' in symbol_upper:
            return AssetType.COMMODITY

        if 'SI=F' in symbol or 'CL=F' in symbol:
            return AssetType.COMMODITY

        # Default to stock
        return AssetType.STOCK

    def get_preferred_sources(self, asset_type: AssetType) -> List[Tuple[DataSource, BaseDataProvider]]:
        """Get ordered list of preferred data sources for asset type"""
        if asset_type == AssetType.CRYPTO:
            return [
                (DataSource.BINANCE, self.binance),
                (DataSource.YAHOO, self.yahoo),
            ]
        elif asset_type == AssetType.FOREX:
            return [
                (DataSource.ALPHA_VANTAGE, self.alpha_vantage),
                (DataSource.YAHOO, self.yahoo),
            ]
        else:  # Commodity, Stock
            return [
                (DataSource.YAHOO, self.yahoo),
            ]

    def fetch_mtf_data(self, symbol: str) -> Dict:
        """
        Fetch Multi-Timeframe data with automatic source selection

        Returns:
            Dict with H4, H1, M15, M5 data and metadata
        """
        asset_type = self.detect_asset_type(symbol)
        sources = self.get_preferred_sources(asset_type)

        result = {
            'symbol': symbol,
            'asset_type': asset_type.value,
            'fetch_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'sources_used': [],
            'H4': None,
            'H1': None,
            'M15': None,
            'M5': None,
        }

        timeframes = ['H4', 'H1', 'M15', 'M5']

        for tf in timeframes:
            df = None
            source_used = None

            # Try each source in order of preference
            for source_name, provider in sources:
                try:
                    df = provider.fetch_ohlcv(symbol, tf, limit=200)
                    if df is not None and len(df) > 0:
                        source_used = source_name.value
                        break
                except Exception as e:
                    print(f"Error with {source_name.value} for {tf}: {e}")
                    continue

            result[tf] = df
            if source_used:
                result['sources_used'].append(f"{tf}:{source_used}")

            time.sleep(0.2)  # Small delay between timeframes

        # Log the fetch
        self.fetch_log.append({
            'timestamp': result['fetch_time'],
            'symbol': symbol,
            'sources': result['sources_used']
        })

        return result

    def get_current_price(self, symbol: str) -> Optional[Dict]:
        """Get current price from best available source"""
        asset_type = self.detect_asset_type(symbol)

        if asset_type == AssetType.CRYPTO:
            price = self.binance.get_ticker_price(symbol)
            if price:
                return {
                    'price': price,
                    'source': 'binance',
                    'time': datetime.utcnow().isoformat()
                }

        # Fallback: get latest close from OHLCV
        sources = self.get_preferred_sources(asset_type)
        for source_name, provider in sources:
            try:
                df = provider.fetch_ohlcv(symbol, 'M5', limit=1)
                if df is not None and len(df) > 0:
                    return {
                        'price': df['close'].iloc[-1],
                        'source': source_name.value,
                        'time': datetime.utcnow().isoformat()
                    }
            except:
                continue

        return None

    def verify_data_consistency(self, symbol: str) -> Dict:
        """
        Verify data from multiple sources matches
        Returns consistency report
        """
        prices = {}

        # Get price from each available source
        if self.binance.is_crypto_symbol(symbol):
            bp = self.binance.get_ticker_price(symbol)
            if bp:
                prices['binance'] = bp

        # Yahoo
        try:
            ydf = self.yahoo.fetch_ohlcv(symbol, 'M5', limit=1)
            if ydf is not None and len(ydf) > 0:
                prices['yahoo'] = ydf['close'].iloc[-1]
        except:
            pass

        if len(prices) < 2:
            return {
                'verified': False,
                'reason': 'Insufficient sources',
                'prices': prices
            }

        # Check if prices are within 0.5% of each other
        price_list = list(prices.values())
        avg_price = sum(price_list) / len(price_list)
        max_deviation = max(abs(p - avg_price) / avg_price for p in price_list)

        return {
            'verified': max_deviation < 0.005,  # 0.5% tolerance
            'deviation': f"{max_deviation*100:.2f}%",
            'prices': prices,
            'average': avg_price
        }


# Convenience function
def create_data_manager(alpha_vantage_key: str = None) -> MultiSourceDataManager:
    """Create a configured data manager"""
    return MultiSourceDataManager(alpha_vantage_key)


if __name__ == "__main__":
    # Test the providers
    print("Testing Multi-Source Data Providers\n")

    manager = create_data_manager()

    # Test Bitcoin (should use Binance)
    print("=" * 50)
    print("Testing BTC-USD (Crypto)")
    print("=" * 50)
    data = manager.fetch_mtf_data('BTC-USD')
    print(f"Symbol: {data['symbol']}")
    print(f"Asset Type: {data['asset_type']}")
    print(f"Sources: {data['sources_used']}")
    for tf in ['H4', 'H1', 'M15', 'M5']:
        if data[tf] is not None:
            print(f"  {tf}: {len(data[tf])} candles, last close: {data[tf]['close'].iloc[-1]:.2f}")

    # Test price verification
    print("\nPrice Verification:")
    verify = manager.verify_data_consistency('BTC-USD')
    print(f"  Verified: {verify['verified']}")
    print(f"  Prices: {verify['prices']}")

    # Test Gold (should use Yahoo)
    print("\n" + "=" * 50)
    print("Testing GC=F (Gold)")
    print("=" * 50)
    data = manager.fetch_mtf_data('GC=F')
    print(f"Symbol: {data['symbol']}")
    print(f"Asset Type: {data['asset_type']}")
    print(f"Sources: {data['sources_used']}")
    for tf in ['H4', 'H1', 'M15', 'M5']:
        if data[tf] is not None:
            print(f"  {tf}: {len(data[tf])} candles, last close: {data[tf]['close'].iloc[-1]:.2f}")
