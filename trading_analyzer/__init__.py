"""
Market Decision Engine
Capital preservation first. Growth second.
"""
from .indicators import Indicators
from .analyzer import DecisionEngine, Decision, Direction, Regime, Analysis
from .data_fetcher import DataFetcher

__version__ = "2.0.0"
