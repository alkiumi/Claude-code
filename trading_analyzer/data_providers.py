"""
Multi-Source Data Providers - Enhanced Version
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Primary Sources:
- Binance API (Crypto - Real-time, No API key needed)
- Twelve Data (Forex/Commodities - 800 calls/day free)
- CoinGecko (Crypto - Unlimited free)

Fallback Sources:
- Yahoo Finance (All assets)
- Alpha Vantage (Forex - 25 calls/day)

Features:
- Automatic failover between sources
- Rate limiting protection
- Data validation
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from abc import ABC, abstractmethod
from enum import Enum
import time
import json
import os


class DataSource(Enum):
    BINANCE = "binance"
    TWELVE_DATA = "twelvedata"
    COINGECKO = "coingecko"
    FINNHUB = "finnhub"
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


class TwelveDataProvider(BaseDataProvider):
    """
    Twelve Data API - Professional grade data
    Free tier: 800 API calls/day, 8 calls/minute
    Supports: Forex, Crypto, Stocks, Commodities
    """

    BASE_URL = "https://api.twelvedata.com"

    INTERVAL_MAP = {
        'M1': '1min',
        'M5': '5min',
        'M15': '15min',
        'M30': '30min',
        'H1': '1h',
        'H4': '4h',
        'D1': '1day',
        'W1': '1week',
    }

    # Symbol mappings for commodities
    SYMBOL_MAP = {
        'GC=F': 'XAU/USD',      # Gold
        'GOLD': 'XAU/USD',
        'XAUUSD': 'XAU/USD',
        'SI=F': 'XAG/USD',      # Silver
        'CL=F': 'WTI/USD',      # Oil WTI
        'OIL': 'WTI/USD',
        'USOIL': 'WTI/USD',
        'BTC-USD': 'BTC/USD',
        'ETH-USD': 'ETH/USD',
        'EURUSD=X': 'EUR/USD',
        'GBPUSD=X': 'GBP/USD',
    }

    def __init__(self, api_key: str = None):
        super().__init__()
        # Free demo key or user's key
        self.api_key = api_key or os.environ.get('TWELVE_DATA_KEY', 'demo')
        self.rate_limit_delay = 8  # 8 calls per minute for free tier

    def get_supported_intervals(self) -> List[str]:
        return list(self.INTERVAL_MAP.keys())

    def resolve_symbol(self, symbol: str) -> str:
        """Convert symbol to Twelve Data format"""
        symbol_upper = symbol.upper()
        return self.SYMBOL_MAP.get(symbol_upper, symbol_upper)

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int = 200
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from Twelve Data"""
        try:
            self._respect_rate_limit()

            td_symbol = self.resolve_symbol(symbol)
            td_interval = self.INTERVAL_MAP.get(interval, '15min')

            url = f"{self.BASE_URL}/time_series"
            params = {
                'symbol': td_symbol,
                'interval': td_interval,
                'outputsize': min(limit, 5000),
                'apikey': self.api_key,
                'format': 'JSON'
            }

            response = self.session.get(url, params=params, timeout=15)

            if response.status_code != 200:
                print(f"Twelve Data API error: {response.status_code}")
                return None

            data = response.json()

            if 'code' in data and data['code'] != 200:
                print(f"Twelve Data error: {data.get('message', 'Unknown error')}")
                return None

            if 'values' not in data:
                return None

            records = []
            for candle in data['values']:
                records.append({
                    'timestamp': candle['datetime'],
                    'open': float(candle['open']),
                    'high': float(candle['high']),
                    'low': float(candle['low']),
                    'close': float(candle['close']),
                    'volume': float(candle.get('volume', 0))
                })

            df = pd.DataFrame(records)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)

            return df.tail(limit)

        except Exception as e:
            print(f"Twelve Data fetch error: {e}")
            return None

    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price"""
        try:
            self._respect_rate_limit()
            td_symbol = self.resolve_symbol(symbol)

            url = f"{self.BASE_URL}/price"
            params = {
                'symbol': td_symbol,
                'apikey': self.api_key
            }

            response = self.session.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                return float(data.get('price', 0))
            return None

        except Exception:
            return None


class CoinGeckoProvider(BaseDataProvider):
    """
    CoinGecko API - Free unlimited crypto data
    No API key required for basic endpoints
    Rate limit: 10-50 calls/minute
    """

    BASE_URL = "https://api.coingecko.com/api/v3"

    # Map symbols to CoinGecko IDs
    COIN_MAP = {
        'BTC': 'bitcoin',
        'BTC-USD': 'bitcoin',
        'BTCUSD': 'bitcoin',
        'ETH': 'ethereum',
        'ETH-USD': 'ethereum',
        'BNB': 'binancecoin',
        'XRP': 'ripple',
        'SOL': 'solana',
        'ADA': 'cardano',
        'DOGE': 'dogecoin',
        'AVAX': 'avalanche-2',
        'DOT': 'polkadot',
        'MATIC': 'matic-network',
        'LINK': 'chainlink',
    }

    def __init__(self):
        super().__init__()
        self.rate_limit_delay = 1.5  # Conservative rate limiting

    def get_supported_intervals(self) -> List[str]:
        return ['M5', 'M15', 'M30', 'H1', 'H4', 'D1']

    def resolve_coin_id(self, symbol: str) -> Optional[str]:
        """Convert symbol to CoinGecko ID"""
        symbol_clean = symbol.upper().replace('-USD', '').replace('USDT', '')
        return self.COIN_MAP.get(symbol_clean)

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int = 200
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from CoinGecko"""
        try:
            self._respect_rate_limit()

            coin_id = self.resolve_coin_id(symbol)
            if not coin_id:
                return None

            # Determine days based on interval
            if interval in ['M1', 'M5', 'M15']:
                days = 1
            elif interval in ['M30', 'H1']:
                days = 7
            elif interval == 'H4':
                days = 30
            else:
                days = 90

            url = f"{self.BASE_URL}/coins/{coin_id}/ohlc"
            params = {
                'vs_currency': 'usd',
                'days': days
            }

            response = self.session.get(url, params=params, timeout=15)

            if response.status_code != 200:
                print(f"CoinGecko API error: {response.status_code}")
                return None

            data = response.json()

            if not data:
                return None

            # CoinGecko OHLC format: [timestamp, open, high, low, close]
            records = []
            for candle in data:
                records.append({
                    'timestamp': candle[0],
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': 0  # CoinGecko OHLC doesn't include volume
                })

            df = pd.DataFrame(records)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)

            return df.tail(limit)

        except Exception as e:
            print(f"CoinGecko fetch error: {e}")
            return None

    def get_price(self, symbol: str) -> Optional[Dict]:
        """Get current price with 24h change"""
        try:
            self._respect_rate_limit()

            coin_id = self.resolve_coin_id(symbol)
            if not coin_id:
                return None

            url = f"{self.BASE_URL}/simple/price"
            params = {
                'ids': coin_id,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true'
            }

            response = self.session.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if coin_id in data:
                    return {
                        'price': data[coin_id]['usd'],
                        'change_24h': data[coin_id].get('usd_24h_change', 0),
                        'volume_24h': data[coin_id].get('usd_24h_vol', 0)
                    }
            return None

        except Exception:
            return None


class FinnhubProvider(BaseDataProvider):
    """
    Finnhub API - Real-time market data
    Free tier: 60 API calls/minute
    Supports: Stocks, Forex, Crypto
    """

    BASE_URL = "https://finnhub.io/api/v1"

    INTERVAL_MAP = {
        'M1': '1',
        'M5': '5',
        'M15': '15',
        'M30': '30',
        'H1': '60',
        'D1': 'D',
        'W1': 'W',
    }

    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key or os.environ.get('FINNHUB_KEY', '')
        self.rate_limit_delay = 1  # 60 calls/minute

    def get_supported_intervals(self) -> List[str]:
        return list(self.INTERVAL_MAP.keys())

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int = 200
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from Finnhub"""
        if not self.api_key:
            return None

        try:
            self._respect_rate_limit()

            fh_resolution = self.INTERVAL_MAP.get(interval, '15')

            # Calculate time range
            now = int(time.time())
            if interval in ['M1', 'M5', 'M15']:
                from_time = now - (86400 * 2)  # 2 days
            elif interval in ['M30', 'H1']:
                from_time = now - (86400 * 7)  # 7 days
            else:
                from_time = now - (86400 * 365)  # 1 year

            url = f"{self.BASE_URL}/stock/candle"
            params = {
                'symbol': symbol.upper(),
                'resolution': fh_resolution,
                'from': from_time,
                'to': now,
                'token': self.api_key
            }

            response = self.session.get(url, params=params, timeout=15)

            if response.status_code != 200:
                return None

            data = response.json()

            if data.get('s') != 'ok':
                return None

            df = pd.DataFrame({
                'timestamp': data['t'],
                'open': data['o'],
                'high': data['h'],
                'low': data['l'],
                'close': data['c'],
                'volume': data['v']
            })

            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)

            return df.tail(limit)

        except Exception as e:
            print(f"Finnhub fetch error: {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get real-time quote"""
        if not self.api_key:
            return None

        try:
            self._respect_rate_limit()

            url = f"{self.BASE_URL}/quote"
            params = {
                'symbol': symbol.upper(),
                'token': self.api_key
            }

            response = self.session.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()
                return {
                    'price': data.get('c', 0),
                    'open': data.get('o', 0),
                    'high': data.get('h', 0),
                    'low': data.get('l', 0),
                    'prev_close': data.get('pc', 0),
                    'change': data.get('d', 0),
                    'change_pct': data.get('dp', 0)
                }
            return None

        except Exception:
            return None


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

    Priority Order:
    ━━━━━━━━━━━━━━━
    Crypto:      Binance → CoinGecko → Yahoo
    Forex:       Twelve Data → Alpha Vantage → Yahoo
    Commodities: Twelve Data → Yahoo
    Stocks:      Finnhub → Yahoo
    """

    def __init__(self, alpha_vantage_key: str = None, twelve_data_key: str = None, finnhub_key: str = None):
        # Primary providers
        self.binance = BinanceProvider()
        self.twelve_data = TwelveDataProvider(twelve_data_key)
        self.coingecko = CoinGeckoProvider()

        # Secondary providers
        self.finnhub = FinnhubProvider(finnhub_key)
        self.alpha_vantage = AlphaVantageProvider(alpha_vantage_key)

        # Fallback
        self.yahoo = YahooProvider()

        # Webhook handler
        self.tradingview = TradingViewWebhook()

        self.fetch_log = []
        self.source_stats = {source.value: {'success': 0, 'fail': 0} for source in DataSource}

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
        if any(x in symbol_upper for x in ['GC=F', 'GOLD', 'XAU', 'SI=F', 'CL=F', 'OIL', 'WTI']):
            return AssetType.COMMODITY

        # Default to stock
        return AssetType.STOCK

    def get_preferred_sources(self, asset_type: AssetType) -> List[Tuple[DataSource, BaseDataProvider]]:
        """Get ordered list of preferred data sources for asset type"""
        if asset_type == AssetType.CRYPTO:
            return [
                (DataSource.BINANCE, self.binance),
                (DataSource.COINGECKO, self.coingecko),
                (DataSource.YAHOO, self.yahoo),
            ]
        elif asset_type == AssetType.FOREX:
            return [
                (DataSource.TWELVE_DATA, self.twelve_data),
                (DataSource.ALPHA_VANTAGE, self.alpha_vantage),
                (DataSource.YAHOO, self.yahoo),
            ]
        elif asset_type == AssetType.COMMODITY:
            return [
                (DataSource.TWELVE_DATA, self.twelve_data),
                (DataSource.YAHOO, self.yahoo),
            ]
        else:  # Stock
            return [
                (DataSource.FINNHUB, self.finnhub),
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
            'sources_tried': [],
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
                        self.source_stats[source_used]['success'] += 1
                        break
                    else:
                        self.source_stats[source_name.value]['fail'] += 1
                        result['sources_tried'].append(f"{tf}:{source_name.value}:fail")
                except Exception as e:
                    self.source_stats[source_name.value]['fail'] += 1
                    result['sources_tried'].append(f"{tf}:{source_name.value}:error")
                    continue

            result[tf] = df
            if source_used:
                result['sources_used'].append(f"{tf}:{source_used}")

            time.sleep(0.15)  # Small delay between timeframes

        # Log the fetch
        self.fetch_log.append({
            'timestamp': result['fetch_time'],
            'symbol': symbol,
            'sources': result['sources_used']
        })

        return result

    def get_source_stats(self) -> Dict:
        """Get statistics about data source usage"""
        stats = {}
        for source, data in self.source_stats.items():
            total = data['success'] + data['fail']
            if total > 0:
                stats[source] = {
                    'success': data['success'],
                    'fail': data['fail'],
                    'success_rate': f"{(data['success']/total)*100:.1f}%"
                }
        return stats

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
def create_data_manager(
    alpha_vantage_key: str = None,
    twelve_data_key: str = None,
    finnhub_key: str = None
) -> MultiSourceDataManager:
    """
    Create a configured data manager

    API Keys (optional - will use env variables or demo keys):
    - TWELVE_DATA_KEY: For forex/commodities (800 calls/day free)
    - FINNHUB_KEY: For stocks (60 calls/min free)
    - ALPHA_VANTAGE_KEY: For forex backup (25 calls/day free)
    """
    return MultiSourceDataManager(
        alpha_vantage_key=alpha_vantage_key,
        twelve_data_key=twelve_data_key,
        finnhub_key=finnhub_key
    )


if __name__ == "__main__":
    # Test the providers
    print("=" * 60)
    print("  Testing Multi-Source Data Providers (Enhanced)")
    print("=" * 60)

    manager = create_data_manager()

    print("\n📊 Available Data Sources:")
    print("  • Binance      - Crypto (real-time, free)")
    print("  • Twelve Data  - Forex/Commodities (800/day free)")
    print("  • CoinGecko    - Crypto (unlimited free)")
    print("  • Finnhub      - Stocks (60/min free)")
    print("  • Yahoo        - Fallback (free)")

    # Test Bitcoin (should use Binance)
    print("\n" + "=" * 50)
    print("🪙 Testing BTC-USD (Crypto)")
    print("=" * 50)
    data = manager.fetch_mtf_data('BTC-USD')
    print(f"Symbol: {data['symbol']}")
    print(f"Asset Type: {data['asset_type']}")
    print(f"Sources Used: {data['sources_used']}")
    for tf in ['H4', 'H1', 'M15', 'M5']:
        if data[tf] is not None:
            print(f"  {tf}: {len(data[tf])} candles, last: ${data[tf]['close'].iloc[-1]:,.2f}")

    # Test Gold (should use Twelve Data or Yahoo)
    print("\n" + "=" * 50)
    print("🥇 Testing GOLD (Commodity)")
    print("=" * 50)
    data = manager.fetch_mtf_data('GC=F')
    print(f"Symbol: {data['symbol']}")
    print(f"Asset Type: {data['asset_type']}")
    print(f"Sources Used: {data['sources_used']}")
    for tf in ['H4', 'H1', 'M15', 'M5']:
        if data[tf] is not None:
            print(f"  {tf}: {len(data[tf])} candles, last: ${data[tf]['close'].iloc[-1]:,.2f}")

    # Test EUR/USD (should use Twelve Data or Alpha Vantage)
    print("\n" + "=" * 50)
    print("💱 Testing EUR/USD (Forex)")
    print("=" * 50)
    data = manager.fetch_mtf_data('EURUSD=X')
    print(f"Symbol: {data['symbol']}")
    print(f"Asset Type: {data['asset_type']}")
    print(f"Sources Used: {data['sources_used']}")
    for tf in ['H4', 'H1', 'M15', 'M5']:
        if data[tf] is not None:
            print(f"  {tf}: {len(data[tf])} candles, last: {data[tf]['close'].iloc[-1]:.5f}")

    # Show source statistics
    print("\n" + "=" * 50)
    print("📈 Source Statistics")
    print("=" * 50)
    stats = manager.get_source_stats()
    for source, data in stats.items():
        print(f"  {source}: {data['success']} success, {data['fail']} fail ({data['success_rate']})")
