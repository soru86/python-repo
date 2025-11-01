"""
Moving Average Crossover Strategy

This strategy implements a simple moving average crossover system:
- Uses two moving averages (fast and slow)
- Generates BUY signals when fast MA crosses above slow MA
- Generates SELL signals when fast MA crosses below slow MA
- Includes additional filters for trend strength and volume
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import logging

from .base_strategy import BaseStrategy, StrategyConfig, Signal, Position

logger = logging.getLogger(__name__)

class MovingAverageStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy
    
    Parameters:
    - fast_period: Fast moving average period (default: 10)
    - slow_period: Slow moving average period (default: 20)
    - min_trend_strength: Minimum trend strength for signal (default: 0.1)
    - volume_threshold: Minimum volume threshold (default: 1000)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy-specific parameters
        self.fast_period = self.parameters.get('fast_period', 10)
        self.slow_period = self.parameters.get('slow_period', 20)
        self.min_trend_strength = self.parameters.get('min_trend_strength', 0.1)
        self.volume_threshold = self.parameters.get('volume_threshold', 1000)
        
        # Technical indicators storage
        self.fast_ma = {}
        self.slow_ma = {}
        self.trend_strength = {}
        
        logger.info(f"Initialized Moving Average Strategy with fast_period={self.fast_period}, slow_period={self.slow_period}")
    
    def _generate_signals(self):
        """Generate trading signals based on moving average crossovers"""
        for symbol in self.symbols:
            if symbol not in self.price_history or len(self.price_history[symbol]) < self.slow_period:
                continue
            
            # Calculate moving averages
            self._calculate_moving_averages(symbol)
            
            # Check for crossover signals
            signal = self._check_crossover_signal(symbol)
            
            if signal:
                self.add_signal(signal)
    
    def _calculate_moving_averages(self, symbol: str):
        """Calculate fast and slow moving averages"""
        if len(self.price_history[symbol]) < self.slow_period:
            return
        
        prices = [data['price'] for data in self.price_history[symbol]]
        
        # Calculate fast moving average
        if len(prices) >= self.fast_period:
            fast_ma = np.mean(prices[-self.fast_period:])
            self.fast_ma[symbol] = fast_ma
        
        # Calculate slow moving average
        if len(prices) >= self.slow_period:
            slow_ma = np.mean(prices[-self.slow_period:])
            self.slow_ma[symbol] = slow_ma
        
        # Calculate trend strength (slope of slow MA)
        if len(prices) >= self.slow_period * 2:
            recent_slow_ma = np.mean(prices[-self.slow_period:])
            older_slow_ma = np.mean(prices[-self.slow_period*2:-self.slow_period])
            trend_strength = (recent_slow_ma - older_slow_ma) / older_slow_ma
            self.trend_strength[symbol] = trend_strength
    
    def _check_crossover_signal(self, symbol: str) -> Optional[Signal]:
        """Check for moving average crossover signals"""
        if symbol not in self.fast_ma or symbol not in self.slow_ma:
            return None
        
        current_fast = self.fast_ma[symbol]
        current_slow = self.slow_ma[symbol]
        
        # Get previous values for crossover detection
        if len(self.price_history[symbol]) < self.slow_period + 1:
            return None
        
        prev_prices = [data['price'] for data in self.price_history[symbol][-self.slow_period-1:-1]]
        prev_fast = np.mean(prev_prices[-self.fast_period:])
        prev_slow = np.mean(prev_prices[-self.slow_period:])
        
        # Check volume threshold
        recent_volume = sum([data['volume'] for data in self.price_history[symbol][-5:]])
        if recent_volume < self.volume_threshold:
            return None
        
        # Check trend strength
        if symbol in self.trend_strength:
            if abs(self.trend_strength[symbol]) < self.min_trend_strength:
                return None
        
        # Detect crossover
        current_price = self.price_history[symbol][-1]['price']
        timestamp = self.price_history[symbol][-1]['timestamp']
        
        # Bullish crossover (fast MA crosses above slow MA)
        if (prev_fast <= prev_slow and current_fast > current_slow):
            confidence = min(abs(current_fast - current_slow) / current_slow, 1.0)
            
            return Signal(
                symbol=symbol,
                signal_type='BUY',
                price=current_price,
                timestamp=timestamp,
                confidence=confidence,
                strategy_name=self.strategy_name,
                additional_data={
                    'fast_ma': current_fast,
                    'slow_ma': current_slow,
                    'trend_strength': self.trend_strength.get(symbol, 0)
                }
            )
        
        # Bearish crossover (fast MA crosses below slow MA)
        elif (prev_fast >= prev_slow and current_fast < current_slow):
            confidence = min(abs(current_fast - current_slow) / current_slow, 1.0)
            
            return Signal(
                symbol=symbol,
                signal_type='SELL',
                price=current_price,
                timestamp=timestamp,
                confidence=confidence,
                strategy_name=self.strategy_name,
                additional_data={
                    'fast_ma': current_fast,
                    'slow_ma': current_slow,
                    'trend_strength': self.trend_strength.get(symbol, 0)
                }
            )
        
        return None
    
    def get_strategy_indicators(self, symbol: str) -> Dict[str, float]:
        """Get current indicator values for a symbol"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < self.slow_period:
            return {}
        
        self._calculate_moving_averages(symbol)
        
        return {
            'fast_ma': self.fast_ma.get(symbol, 0),
            'slow_ma': self.slow_ma.get(symbol, 0),
            'trend_strength': self.trend_strength.get(symbol, 0),
            'current_price': self.price_history[symbol][-1]['price'] if self.price_history[symbol] else 0
        } 