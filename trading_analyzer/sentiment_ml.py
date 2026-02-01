"""
Sentiment Analysis & ML/AI Module
- Fear & Greed Index
- News Sentiment Analysis
- Pattern Recognition
- Price Prediction
- Trend Classification
"""
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import json


class Sentiment(Enum):
    EXTREME_FEAR = "خوف شديد"
    FEAR = "خوف"
    NEUTRAL = "محايد"
    GREED = "طمع"
    EXTREME_GREED = "طمع شديد"


class Pattern(Enum):
    BULLISH_ENGULFING = "ابتلاع صاعد"
    BEARISH_ENGULFING = "ابتلاع هابط"
    HAMMER = "مطرقة"
    SHOOTING_STAR = "نجمة ساقطة"
    DOJI = "دوجي"
    MORNING_STAR = "نجمة الصباح"
    EVENING_STAR = "نجمة المساء"
    THREE_WHITE_SOLDIERS = "ثلاثة جنود بيض"
    THREE_BLACK_CROWS = "ثلاثة غربان سود"
    DOUBLE_TOP = "قمة مزدوجة"
    DOUBLE_BOTTOM = "قاع مزدوج"
    HEAD_SHOULDERS = "رأس وكتفين"
    NONE = "لا يوجد"


class TrendPrediction(Enum):
    STRONG_UP = "صعود قوي"
    UP = "صعود"
    SIDEWAYS = "عرضي"
    DOWN = "هبوط"
    STRONG_DOWN = "هبوط قوي"


@dataclass
class SentimentResult:
    """Complete sentiment analysis result"""
    fear_greed_index: int  # 0-100
    fear_greed_label: Sentiment
    news_sentiment: float  # -1 to 1
    news_headlines: List[str]
    social_mentions: int
    overall_sentiment: Sentiment
    sentiment_score: float  # -100 to 100
    fetch_time: str


@dataclass
class PatternResult:
    """Pattern recognition result"""
    patterns_found: List[Tuple[Pattern, str]]  # (pattern, timeframe)
    pattern_bias: str  # صاعد, هابط, محايد
    confidence: float  # 0-100


@dataclass
class MLPrediction:
    """ML prediction result"""
    trend_prediction: TrendPrediction
    predicted_direction: str  # UP, DOWN, SIDEWAYS
    confidence: float  # 0-100
    support_levels: List[float]
    resistance_levels: List[float]
    predicted_range: Tuple[float, float]  # (low, high) for next period
    features_used: List[str]


@dataclass
class AIAnalysis:
    """Complete AI/ML analysis"""
    sentiment: SentimentResult
    patterns: PatternResult
    ml_prediction: MLPrediction
    ai_score: float  # -100 to 100 (negative=bearish, positive=bullish)
    ai_recommendation: str
    confidence: float


class FearGreedFetcher:
    """Fetch Fear & Greed Index from alternative.me"""

    API_URL = "https://api.alternative.me/fng/"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.cache = {}
        self.cache_time = None
        self.cache_duration = 300  # 5 minutes

    def fetch(self) -> Optional[Dict]:
        """Fetch current Fear & Greed Index"""
        try:
            # Check cache
            if self.cache_time and (datetime.now() - self.cache_time).seconds < self.cache_duration:
                return self.cache

            response = self.session.get(self.API_URL, params={'limit': 1}, timeout=10)

            if response.status_code != 200:
                return None

            data = response.json()

            if 'data' not in data or not data['data']:
                return None

            fng_data = data['data'][0]

            result = {
                'value': int(fng_data['value']),
                'classification': fng_data['value_classification'],
                'timestamp': datetime.fromtimestamp(int(fng_data['timestamp'])).isoformat()
            }

            self.cache = result
            self.cache_time = datetime.now()

            return result

        except Exception as e:
            print(f"Fear & Greed fetch error: {e}")
            return None

    def get_sentiment(self, value: int) -> Sentiment:
        """Convert FNG value to Sentiment enum"""
        if value <= 20:
            return Sentiment.EXTREME_FEAR
        elif value <= 40:
            return Sentiment.FEAR
        elif value <= 60:
            return Sentiment.NEUTRAL
        elif value <= 80:
            return Sentiment.GREED
        else:
            return Sentiment.EXTREME_GREED


class NewsSentimentAnalyzer:
    """Analyze news sentiment using keyword-based approach"""

    # Bullish keywords
    BULLISH_KEYWORDS = [
        'bullish', 'surge', 'soar', 'rally', 'breakout', 'moon', 'pump',
        'buy', 'long', 'growth', 'adoption', 'institutional', 'etf approved',
        'all-time high', 'ath', 'record', 'milestone', 'breakthrough',
        'positive', 'optimistic', 'uptrend', 'support', 'accumulation',
        'halving', 'upgrade', 'partnership', 'bullrun', 'recovery'
    ]

    # Bearish keywords
    BEARISH_KEYWORDS = [
        'bearish', 'crash', 'dump', 'plunge', 'selloff', 'correction',
        'sell', 'short', 'decline', 'ban', 'regulation', 'hack', 'scam',
        'fraud', 'investigation', 'lawsuit', 'warning', 'risk',
        'negative', 'pessimistic', 'downtrend', 'resistance', 'distribution',
        'bankruptcy', 'insolvency', 'fear', 'panic', 'capitulation'
    ]

    # News sources
    CRYPTO_PANIC_URL = "https://cryptopanic.com/api/v1/posts/"

    def __init__(self, cryptopanic_token: str = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.cryptopanic_token = cryptopanic_token

    def fetch_crypto_news(self, symbol: str = 'BTC') -> List[Dict]:
        """Fetch news from CryptoPanic (if token available) or use fallback"""
        try:
            # Try CryptoPanic if token available
            if self.cryptopanic_token:
                params = {
                    'auth_token': self.cryptopanic_token,
                    'currencies': symbol,
                    'filter': 'hot',
                    'public': 'true'
                }
                response = self.session.get(self.CRYPTO_PANIC_URL, params=params, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    if 'results' in data:
                        return [{'title': r['title'], 'source': r.get('source', {}).get('title', 'Unknown')}
                                for r in data['results'][:10]]

            # Fallback: Return empty list (we'll use Fear & Greed as primary)
            return []

        except Exception as e:
            print(f"News fetch error: {e}")
            return []

    def analyze_text(self, text: str) -> float:
        """Analyze sentiment of text, returns -1 to 1"""
        text_lower = text.lower()

        bullish_count = sum(1 for word in self.BULLISH_KEYWORDS if word in text_lower)
        bearish_count = sum(1 for word in self.BEARISH_KEYWORDS if word in text_lower)

        total = bullish_count + bearish_count
        if total == 0:
            return 0.0

        return (bullish_count - bearish_count) / total

    def analyze_headlines(self, headlines: List[str]) -> float:
        """Analyze multiple headlines, returns average sentiment"""
        if not headlines:
            return 0.0

        sentiments = [self.analyze_text(h) for h in headlines]
        return sum(sentiments) / len(sentiments)


class PatternRecognition:
    """Candlestick and chart pattern recognition"""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.patterns = []

    def detect_all_patterns(self) -> List[Tuple[Pattern, int]]:
        """Detect all patterns in the data"""
        patterns = []

        # Need at least 3 candles
        if len(self.df) < 3:
            return patterns

        # Check last few candles for patterns
        for i in range(-5, 0):
            if abs(i) > len(self.df):
                continue

            # Single candle patterns
            if self._is_doji(i):
                patterns.append((Pattern.DOJI, i))
            if self._is_hammer(i):
                patterns.append((Pattern.HAMMER, i))
            if self._is_shooting_star(i):
                patterns.append((Pattern.SHOOTING_STAR, i))

            # Two candle patterns
            if i < -1:
                if self._is_bullish_engulfing(i):
                    patterns.append((Pattern.BULLISH_ENGULFING, i))
                if self._is_bearish_engulfing(i):
                    patterns.append((Pattern.BEARISH_ENGULFING, i))

        # Three candle patterns (check only most recent)
        if len(self.df) >= 3:
            if self._is_morning_star():
                patterns.append((Pattern.MORNING_STAR, -1))
            if self._is_evening_star():
                patterns.append((Pattern.EVENING_STAR, -1))
            if self._is_three_white_soldiers():
                patterns.append((Pattern.THREE_WHITE_SOLDIERS, -1))
            if self._is_three_black_crows():
                patterns.append((Pattern.THREE_BLACK_CROWS, -1))

        return patterns

    def _is_doji(self, idx: int) -> bool:
        """Detect Doji pattern"""
        row = self.df.iloc[idx]
        body = abs(row['close'] - row['open'])
        total_range = row['high'] - row['low']

        if total_range == 0:
            return False

        return body / total_range < 0.1

    def _is_hammer(self, idx: int) -> bool:
        """Detect Hammer pattern"""
        row = self.df.iloc[idx]
        body = abs(row['close'] - row['open'])
        lower_shadow = min(row['open'], row['close']) - row['low']
        upper_shadow = row['high'] - max(row['open'], row['close'])

        if body == 0:
            return False

        return lower_shadow >= 2 * body and upper_shadow < body * 0.5

    def _is_shooting_star(self, idx: int) -> bool:
        """Detect Shooting Star pattern"""
        row = self.df.iloc[idx]
        body = abs(row['close'] - row['open'])
        lower_shadow = min(row['open'], row['close']) - row['low']
        upper_shadow = row['high'] - max(row['open'], row['close'])

        if body == 0:
            return False

        return upper_shadow >= 2 * body and lower_shadow < body * 0.5

    def _is_bullish_engulfing(self, idx: int) -> bool:
        """Detect Bullish Engulfing pattern"""
        curr = self.df.iloc[idx]
        prev = self.df.iloc[idx - 1]

        # Previous candle bearish, current bullish
        prev_bearish = prev['close'] < prev['open']
        curr_bullish = curr['close'] > curr['open']

        # Current body engulfs previous
        engulfs = curr['open'] < prev['close'] and curr['close'] > prev['open']

        return prev_bearish and curr_bullish and engulfs

    def _is_bearish_engulfing(self, idx: int) -> bool:
        """Detect Bearish Engulfing pattern"""
        curr = self.df.iloc[idx]
        prev = self.df.iloc[idx - 1]

        prev_bullish = prev['close'] > prev['open']
        curr_bearish = curr['close'] < curr['open']
        engulfs = curr['open'] > prev['close'] and curr['close'] < prev['open']

        return prev_bullish and curr_bearish and engulfs

    def _is_morning_star(self) -> bool:
        """Detect Morning Star pattern"""
        if len(self.df) < 3:
            return False

        first = self.df.iloc[-3]
        second = self.df.iloc[-2]
        third = self.df.iloc[-1]

        first_bearish = first['close'] < first['open']
        small_body = abs(second['close'] - second['open']) < abs(first['close'] - first['open']) * 0.3
        third_bullish = third['close'] > third['open']
        closes_above = third['close'] > (first['open'] + first['close']) / 2

        return first_bearish and small_body and third_bullish and closes_above

    def _is_evening_star(self) -> bool:
        """Detect Evening Star pattern"""
        if len(self.df) < 3:
            return False

        first = self.df.iloc[-3]
        second = self.df.iloc[-2]
        third = self.df.iloc[-1]

        first_bullish = first['close'] > first['open']
        small_body = abs(second['close'] - second['open']) < abs(first['close'] - first['open']) * 0.3
        third_bearish = third['close'] < third['open']
        closes_below = third['close'] < (first['open'] + first['close']) / 2

        return first_bullish and small_body and third_bearish and closes_below

    def _is_three_white_soldiers(self) -> bool:
        """Detect Three White Soldiers pattern"""
        if len(self.df) < 3:
            return False

        candles = [self.df.iloc[i] for i in [-3, -2, -1]]

        all_bullish = all(c['close'] > c['open'] for c in candles)
        progressive = candles[1]['close'] > candles[0]['close'] and candles[2]['close'] > candles[1]['close']

        return all_bullish and progressive

    def _is_three_black_crows(self) -> bool:
        """Detect Three Black Crows pattern"""
        if len(self.df) < 3:
            return False

        candles = [self.df.iloc[i] for i in [-3, -2, -1]]

        all_bearish = all(c['close'] < c['open'] for c in candles)
        progressive = candles[1]['close'] < candles[0]['close'] and candles[2]['close'] < candles[1]['close']

        return all_bearish and progressive


class SupportResistanceDetector:
    """Detect support and resistance levels using clustering"""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def find_levels(self, num_levels: int = 3) -> Tuple[List[float], List[float]]:
        """Find support and resistance levels"""
        if len(self.df) < 20:
            return [], []

        # Find local minima (support) and maxima (resistance)
        highs = self.df['high'].values
        lows = self.df['low'].values

        # Simple peak detection
        resistance_candidates = []
        support_candidates = []

        for i in range(2, len(self.df) - 2):
            # Local maximum
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                resistance_candidates.append(highs[i])

            # Local minimum
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                support_candidates.append(lows[i])

        # Cluster nearby levels
        resistance = self._cluster_levels(resistance_candidates, num_levels)
        support = self._cluster_levels(support_candidates, num_levels)

        return sorted(support), sorted(resistance, reverse=True)

    def _cluster_levels(self, levels: List[float], num_clusters: int) -> List[float]:
        """Cluster nearby levels together"""
        if not levels:
            return []

        levels = sorted(levels)

        if len(levels) <= num_clusters:
            return levels

        # Simple clustering: merge levels within 1% of each other
        clustered = []
        current_cluster = [levels[0]]

        for level in levels[1:]:
            if level <= current_cluster[-1] * 1.01:  # Within 1%
                current_cluster.append(level)
            else:
                clustered.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [level]

        clustered.append(sum(current_cluster) / len(current_cluster))

        # Return most significant levels
        return clustered[:num_clusters]


class TrendPredictor:
    """ML-based trend prediction using technical features"""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.features = {}

    def calculate_features(self) -> Dict:
        """Calculate features for prediction"""
        if len(self.df) < 50:
            return {}

        close = self.df['close'].values
        high = self.df['high'].values
        low = self.df['low'].values
        volume = self.df['volume'].values if 'volume' in self.df.columns else np.ones(len(close))

        features = {}

        # Price momentum
        features['momentum_5'] = (close[-1] - close[-5]) / close[-5] * 100 if close[-5] != 0 else 0
        features['momentum_10'] = (close[-1] - close[-10]) / close[-10] * 100 if close[-10] != 0 else 0
        features['momentum_20'] = (close[-1] - close[-20]) / close[-20] * 100 if close[-20] != 0 else 0

        # Volatility
        returns = np.diff(close) / close[:-1]
        features['volatility'] = np.std(returns[-20:]) * 100

        # Trend strength (using linear regression slope)
        x = np.arange(20)
        y = close[-20:]
        slope = np.polyfit(x, y, 1)[0]
        features['trend_slope'] = slope / close[-1] * 100

        # RSI-like momentum
        gains = np.maximum(np.diff(close[-15:]), 0)
        losses = np.abs(np.minimum(np.diff(close[-15:]), 0))
        avg_gain = np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses) if len(losses) > 0 else 0.0001
        rs = avg_gain / avg_loss
        features['rsi'] = 100 - (100 / (1 + rs))

        # Volume trend
        if np.mean(volume[-20:]) > 0:
            features['volume_trend'] = (np.mean(volume[-5:]) / np.mean(volume[-20:]) - 1) * 100
        else:
            features['volume_trend'] = 0

        # Price position
        high_20 = np.max(high[-20:])
        low_20 = np.min(low[-20:])
        range_20 = high_20 - low_20 if high_20 != low_20 else 1
        features['price_position'] = (close[-1] - low_20) / range_20 * 100

        # Candle patterns score
        bullish_candles = sum(1 for i in range(-5, 0) if self.df['close'].iloc[i] > self.df['open'].iloc[i])
        features['bullish_candles'] = bullish_candles / 5 * 100

        self.features = features
        return features

    def predict(self) -> Tuple[TrendPrediction, float, Tuple[float, float]]:
        """Predict trend direction"""
        if not self.features:
            self.calculate_features()

        if not self.features:
            return TrendPrediction.SIDEWAYS, 0, (0, 0)

        # Simple scoring model
        score = 0
        weights = {
            'momentum_5': 2.0,
            'momentum_10': 1.5,
            'momentum_20': 1.0,
            'trend_slope': 3.0,
            'rsi': 0.5,  # RSI contribution (normalize to -50 to 50)
            'volume_trend': 0.5,
            'price_position': 0.3,
            'bullish_candles': 1.0
        }

        # Normalize RSI to -50 to 50
        rsi_normalized = self.features.get('rsi', 50) - 50

        score += self.features.get('momentum_5', 0) * weights['momentum_5']
        score += self.features.get('momentum_10', 0) * weights['momentum_10']
        score += self.features.get('momentum_20', 0) * weights['momentum_20']
        score += self.features.get('trend_slope', 0) * weights['trend_slope']
        score += rsi_normalized * weights['rsi']
        score += self.features.get('volume_trend', 0) * weights['volume_trend']
        score += (self.features.get('price_position', 50) - 50) * weights['price_position']
        score += (self.features.get('bullish_candles', 50) - 50) * weights['bullish_candles']

        # Normalize score
        max_score = sum(abs(v) * 100 for v in weights.values())
        normalized_score = max(-100, min(100, score / max_score * 100))

        # Determine prediction
        if normalized_score > 30:
            prediction = TrendPrediction.STRONG_UP
        elif normalized_score > 10:
            prediction = TrendPrediction.UP
        elif normalized_score < -30:
            prediction = TrendPrediction.STRONG_DOWN
        elif normalized_score < -10:
            prediction = TrendPrediction.DOWN
        else:
            prediction = TrendPrediction.SIDEWAYS

        # Calculate confidence
        confidence = min(100, abs(normalized_score) * 1.5)

        # Predict range
        volatility = self.features.get('volatility', 1)
        current_price = self.df['close'].iloc[-1]
        predicted_low = current_price * (1 - volatility / 100 * 2)
        predicted_high = current_price * (1 + volatility / 100 * 2)

        return prediction, confidence, (predicted_low, predicted_high)


class SentimentMLEngine:
    """
    Complete Sentiment & ML Analysis Engine
    Combines all components for comprehensive analysis
    """

    def __init__(self, cryptopanic_token: str = None):
        self.fear_greed = FearGreedFetcher()
        self.news_analyzer = NewsSentimentAnalyzer(cryptopanic_token)

    def analyze(self, symbol: str, df: pd.DataFrame) -> AIAnalysis:
        """Run complete AI/ML analysis"""

        # 1. Sentiment Analysis
        sentiment = self._analyze_sentiment(symbol)

        # 2. Pattern Recognition
        patterns = self._analyze_patterns(df)

        # 3. ML Prediction
        ml_prediction = self._ml_predict(df)

        # 4. Calculate overall AI score
        ai_score = self._calculate_ai_score(sentiment, patterns, ml_prediction)

        # 5. Generate recommendation
        recommendation = self._generate_recommendation(ai_score, sentiment, patterns, ml_prediction)

        # 6. Overall confidence
        confidence = (sentiment.sentiment_score / 100 * 30 +
                     patterns.confidence * 0.3 +
                     ml_prediction.confidence * 0.4)
        confidence = min(100, max(0, abs(confidence)))

        return AIAnalysis(
            sentiment=sentiment,
            patterns=patterns,
            ml_prediction=ml_prediction,
            ai_score=ai_score,
            ai_recommendation=recommendation,
            confidence=confidence
        )

    def _analyze_sentiment(self, symbol: str) -> SentimentResult:
        """Analyze market sentiment"""

        # Get Fear & Greed Index
        fng_data = self.fear_greed.fetch()

        if fng_data:
            fng_value = fng_data['value']
            fng_label = self.fear_greed.get_sentiment(fng_value)
        else:
            fng_value = 50
            fng_label = Sentiment.NEUTRAL

        # Get news sentiment
        symbol_clean = symbol.replace('-USD', '').replace('=X', '').replace('=F', '')
        news = self.news_analyzer.fetch_crypto_news(symbol_clean)
        headlines = [n['title'] for n in news] if news else []
        news_sentiment = self.news_analyzer.analyze_headlines(headlines)

        # Calculate overall sentiment score (-100 to 100)
        # FNG: 0-100, convert to -50 to 50
        fng_score = (fng_value - 50)
        # News: -1 to 1, convert to -50 to 50
        news_score = news_sentiment * 50

        sentiment_score = fng_score * 0.7 + news_score * 0.3

        # Determine overall sentiment
        if sentiment_score <= -30:
            overall = Sentiment.EXTREME_FEAR
        elif sentiment_score <= -10:
            overall = Sentiment.FEAR
        elif sentiment_score >= 30:
            overall = Sentiment.EXTREME_GREED
        elif sentiment_score >= 10:
            overall = Sentiment.GREED
        else:
            overall = Sentiment.NEUTRAL

        return SentimentResult(
            fear_greed_index=fng_value,
            fear_greed_label=fng_label,
            news_sentiment=news_sentiment,
            news_headlines=headlines[:5],
            social_mentions=0,  # TODO: Add social media integration
            overall_sentiment=overall,
            sentiment_score=sentiment_score,
            fetch_time=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        )

    def _analyze_patterns(self, df: pd.DataFrame) -> PatternResult:
        """Analyze chart patterns"""
        pr = PatternRecognition(df)
        patterns_found = pr.detect_all_patterns()

        # Determine pattern bias
        bullish_patterns = [Pattern.BULLISH_ENGULFING, Pattern.HAMMER, Pattern.MORNING_STAR,
                          Pattern.THREE_WHITE_SOLDIERS, Pattern.DOUBLE_BOTTOM]
        bearish_patterns = [Pattern.BEARISH_ENGULFING, Pattern.SHOOTING_STAR, Pattern.EVENING_STAR,
                          Pattern.THREE_BLACK_CROWS, Pattern.DOUBLE_TOP, Pattern.HEAD_SHOULDERS]

        bullish_count = sum(1 for p, _ in patterns_found if p in bullish_patterns)
        bearish_count = sum(1 for p, _ in patterns_found if p in bearish_patterns)

        if bullish_count > bearish_count:
            bias = "صاعد"
        elif bearish_count > bullish_count:
            bias = "هابط"
        else:
            bias = "محايد"

        # Confidence based on pattern count and agreement
        if patterns_found:
            agreement = abs(bullish_count - bearish_count) / len(patterns_found)
            confidence = min(100, len(patterns_found) * 20 * (1 + agreement))
        else:
            confidence = 0

        return PatternResult(
            patterns_found=[(p, f"candle_{idx}") for p, idx in patterns_found],
            pattern_bias=bias,
            confidence=confidence
        )

    def _ml_predict(self, df: pd.DataFrame) -> MLPrediction:
        """Run ML prediction"""

        # Trend prediction
        predictor = TrendPredictor(df)
        features = predictor.calculate_features()
        prediction, confidence, predicted_range = predictor.predict()

        # Support/Resistance
        sr_detector = SupportResistanceDetector(df)
        support, resistance = sr_detector.find_levels()

        # Direction
        if prediction in [TrendPrediction.STRONG_UP, TrendPrediction.UP]:
            direction = "UP"
        elif prediction in [TrendPrediction.STRONG_DOWN, TrendPrediction.DOWN]:
            direction = "DOWN"
        else:
            direction = "SIDEWAYS"

        return MLPrediction(
            trend_prediction=prediction,
            predicted_direction=direction,
            confidence=confidence,
            support_levels=support,
            resistance_levels=resistance,
            predicted_range=predicted_range,
            features_used=list(features.keys())
        )

    def _calculate_ai_score(self, sentiment: SentimentResult,
                           patterns: PatternResult,
                           ml: MLPrediction) -> float:
        """Calculate overall AI score (-100 to 100)"""

        # Sentiment contribution (30%)
        sentiment_score = sentiment.sentiment_score * 0.3

        # Pattern contribution (30%)
        if patterns.pattern_bias == "صاعد":
            pattern_score = patterns.confidence * 0.3
        elif patterns.pattern_bias == "هابط":
            pattern_score = -patterns.confidence * 0.3
        else:
            pattern_score = 0

        # ML contribution (40%)
        ml_score = 0
        if ml.predicted_direction == "UP":
            ml_score = ml.confidence * 0.4
        elif ml.predicted_direction == "DOWN":
            ml_score = -ml.confidence * 0.4

        total = sentiment_score + pattern_score + ml_score
        return max(-100, min(100, total))

    def _generate_recommendation(self, ai_score: float,
                                sentiment: SentimentResult,
                                patterns: PatternResult,
                                ml: MLPrediction) -> str:
        """Generate Arabic recommendation"""

        if ai_score >= 50:
            return f"📈 إشارة شراء قوية - الثقة {abs(ai_score):.0f}%"
        elif ai_score >= 20:
            return f"📈 إشارة شراء - الثقة {abs(ai_score):.0f}%"
        elif ai_score <= -50:
            return f"📉 إشارة بيع قوية - الثقة {abs(ai_score):.0f}%"
        elif ai_score <= -20:
            return f"📉 إشارة بيع - الثقة {abs(ai_score):.0f}%"
        else:
            return f"⏸️ انتظار - السوق محايد"


def create_sentiment_ml_engine(cryptopanic_token: str = None) -> SentimentMLEngine:
    """Create configured Sentiment/ML engine"""
    return SentimentMLEngine(cryptopanic_token)


if __name__ == "__main__":
    # Test the module
    print("Testing Sentiment & ML Module\n")

    # Create sample data
    import random
    dates = pd.date_range(end=datetime.now(), periods=100, freq='h')
    base_price = 80000
    prices = [base_price]
    for _ in range(99):
        change = random.uniform(-500, 500)
        prices.append(prices[-1] + change)

    df = pd.DataFrame({
        'open': [p - random.uniform(0, 200) for p in prices],
        'high': [p + random.uniform(0, 300) for p in prices],
        'low': [p - random.uniform(0, 300) for p in prices],
        'close': prices,
        'volume': [random.uniform(1000, 5000) for _ in prices]
    }, index=dates)

    # Create engine
    engine = create_sentiment_ml_engine()

    # Run analysis
    result = engine.analyze('BTC-USD', df)

    print("=" * 50)
    print("Sentiment Analysis:")
    print(f"  Fear & Greed: {result.sentiment.fear_greed_index} ({result.sentiment.fear_greed_label.value})")
    print(f"  Overall: {result.sentiment.overall_sentiment.value}")
    print(f"  Score: {result.sentiment.sentiment_score:.1f}")

    print("\nPattern Recognition:")
    print(f"  Patterns: {len(result.patterns.patterns_found)}")
    for p, tf in result.patterns.patterns_found:
        print(f"    - {p.value}")
    print(f"  Bias: {result.patterns.pattern_bias}")

    print("\nML Prediction:")
    print(f"  Trend: {result.ml_prediction.trend_prediction.value}")
    print(f"  Direction: {result.ml_prediction.predicted_direction}")
    print(f"  Confidence: {result.ml_prediction.confidence:.1f}%")
    print(f"  Support: {result.ml_prediction.support_levels}")
    print(f"  Resistance: {result.ml_prediction.resistance_levels}")

    print("\n" + "=" * 50)
    print(f"AI Score: {result.ai_score:.1f}")
    print(f"Recommendation: {result.ai_recommendation}")
    print(f"Overall Confidence: {result.confidence:.1f}%")
