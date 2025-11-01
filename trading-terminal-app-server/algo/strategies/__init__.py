"""
Trading Strategy Templates and Base Classes

This package contains:
- Base strategy classes for different market types
- Strategy templates for common trading patterns
- Strategy configuration and management utilities
"""

from .base_strategy import BaseStrategy
from .moving_average_strategy import MovingAverageStrategy
from .rsi_strategy import RSIStrategy
from .macd_strategy import MACDStrategy
from .bollinger_bands_strategy import BollingerBandsStrategy

__all__ = [
    'BaseStrategy',
    'MovingAverageStrategy', 
    'RSIStrategy',
    'MACDStrategy',
    'BollingerBandsStrategy'
] 