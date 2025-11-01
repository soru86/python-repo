"""
MACD (Moving Average Convergence Divergence) Strategy

This strategy implements MACD-based trading signals:
- Generates BUY signals when MACD line crosses above signal line
- Generates SELL signals when MACD line crosses below signal line
- Includes histogram analysis and divergence detection
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import logging

from .base_strategy import BaseStrategy, StrategyConfig, Signal, Position

logger = logging.getLogger(__name__)

class MACDStrategy(BaseStrategy):
    """
    MACD (Moving Average Convergence Divergence) Strategy
    
    Parameters:
    - fast_period: Fast EMA period (default: 12)
    - slow_period: Slow EMA period (default: 26)
    - signal_period: Signal line period (default: 9)
    - histogram_threshold: Minimum histogram value for signal (default: 0.001)
    - divergence_lookback: Periods to look back for divergence (default: 20)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy-specific parameters
        self.fast_period = self.parameters.get('fast_period', 12)
        self.slow_period = self.parameters.get('slow_period', 26)
        self.signal_period = self.parameters.get('signal_period', 9)
        self.histogram_threshold = self.parameters.get('histogram_threshold', 0.001)
        self.divergence_lookback = self.parameters.get('divergence_lookback', 20)
        
        # Technical indicators storage
        self.macd_line = {}
        self.signal_line = {}
        self.histogram = {}
        self.fast_ema = {}
        self.slow_ema = {}
        
        logger.info(f"Initialized MACD Strategy with fast={self.fast_period}, slow={self.slow_period}, signal={self.signal_period}")
    
    def _generate_signals(self):
        """Generate trading signals based on MACD crossovers"""
        for symbol in self.symbols:
            if symbol not in self.price_history or len(self.price_history[symbol]) < self.slow_period + self.signal_period:
                continue
            
            # Calculate MACD
            self._calculate_macd(symbol)
            
            # Check for MACD signals
            signal = self._check_macd_signal(symbol)
            
            if signal:
                self.add_signal(signal)
    
    def _calculate_macd(self, symbol: str):
        """Calculate MACD for a symbol"""
        if len(self.price_history[symbol]) < self.slow_period + self.signal_period:
            return
        
        prices = [data['price'] for data in self.price_history[symbol]]
        
        # Calculate fast EMA
        fast_ema = self._calculate_ema(prices, self.fast_period)
        self.fast_ema[symbol] = fast_ema
        
        # Calculate slow EMA
        slow_ema = self._calculate_ema(prices, self.slow_period)
        self.slow_ema[symbol] = slow_ema
        
        # Calculate MACD line
        macd_line = fast_ema - slow_ema
        self.macd_line[symbol] = macd_line
        
        # Calculate signal line (EMA of MACD line)
        if len(self.price_history[symbol]) >= self.slow_period + self.signal_period:
            # Get MACD line values for signal calculation
            macd_values = []
            for i in range(len(prices) - self.slow_period + 1):
                period_prices = prices[i:i+self.slow_period]
                fast_ema_val = self._calculate_ema(period_prices, self.fast_period)
                slow_ema_val = self._calculate_ema(period_prices, self.slow_period)
                macd_values.append(fast_ema_val - slow_ema_val)
            
            if len(macd_values) >= self.signal_period:
                signal_line = self._calculate_ema(macd_values, self.signal_period)
                self.signal_line[symbol] = signal_line
                
                # Calculate histogram
                histogram = macd_line - signal_line
                self.histogram[symbol] = histogram
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        # Use simple moving average as initial value
        sma = np.mean(prices[-period:])
        
        # Calculate multiplier
        multiplier = 2 / (period + 1)
        
        # Calculate EMA
        ema = sma
        for price in prices[-period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _check_macd_signal(self, symbol: str) -> Optional[Signal]:
        """Check for MACD-based trading signals"""
        if (symbol not in self.macd_line or symbol not in self.signal_line or 
            symbol not in self.histogram):
            return None
        
        current_macd = self.macd_line[symbol]
        current_signal = self.signal_line[symbol]
        current_histogram = self.histogram[symbol]
        current_price = self.price_history[symbol][-1]['price']
        timestamp = self.price_history[symbol][-1]['timestamp']
        
        # Get previous values for crossover detection
        if len(self.price_history[symbol]) < self.slow_period + self.signal_period + 1:
            return None
        
        # Calculate previous MACD and signal values
        prev_prices = [data['price'] for data in self.price_history[symbol][-self.slow_period-self.signal_period-1:-1]]
        
        if len(prev_prices) >= self.slow_period + self.signal_period:
            prev_fast_ema = self._calculate_ema(prev_prices, self.fast_period)
            prev_slow_ema = self._calculate_ema(prev_prices, self.slow_period)
            prev_macd = prev_fast_ema - prev_slow_ema
            
            # Calculate previous signal line
            prev_macd_values = []
            for i in range(len(prev_prices) - self.slow_period + 1):
                period_prices = prev_prices[i:i+self.slow_period]
                fast_ema_val = self._calculate_ema(period_prices, self.fast_period)
                slow_ema_val = self._calculate_ema(period_prices, self.slow_period)
                prev_macd_values.append(fast_ema_val - slow_ema_val)
            
            if len(prev_macd_values) >= self.signal_period:
                prev_signal = self._calculate_ema(prev_macd_values, self.signal_period)
                
                # Check histogram threshold
                if abs(current_histogram) < self.histogram_threshold:
                    return None
                
                # Bullish crossover (MACD crosses above signal line)
                if (prev_macd <= prev_signal and current_macd > current_signal and 
                    current_histogram > 0):
                    
                    confidence = min(abs(current_macd - current_signal) / abs(current_signal), 1.0)
                    
                    return Signal(
                        symbol=symbol,
                        signal_type='BUY',
                        price=current_price,
                        timestamp=timestamp,
                        confidence=confidence,
                        strategy_name=self.strategy_name,
                        additional_data={
                            'macd': current_macd,
                            'signal': current_signal,
                            'histogram': current_histogram,
                            'divergence': self._check_bullish_divergence(symbol)
                        }
                    )
                
                # Bearish crossover (MACD crosses below signal line)
                elif (prev_macd >= prev_signal and current_macd < current_signal and 
                      current_histogram < 0):
                    
                    confidence = min(abs(current_macd - current_signal) / abs(current_signal), 1.0)
                    
                    return Signal(
                        symbol=symbol,
                        signal_type='SELL',
                        price=current_price,
                        timestamp=timestamp,
                        confidence=confidence,
                        strategy_name=self.strategy_name,
                        additional_data={
                            'macd': current_macd,
                            'signal': current_signal,
                            'histogram': current_histogram,
                            'divergence': self._check_bearish_divergence(symbol)
                        }
                    )
        
        return None
    
    def _check_bullish_divergence(self, symbol: str) -> bool:
        """Check for bullish divergence (price makes lower low, MACD makes higher low)"""
        if len(self.price_history[symbol]) < self.divergence_lookback * 2:
            return False
        
        # Get recent price and MACD data
        recent_prices = [data['price'] for data in self.price_history[symbol][-self.divergence_lookback:]]
        recent_macd_values = []
        
        # Calculate MACD for recent period
        for i in range(len(recent_prices) - self.slow_period + 1):
            period_prices = recent_prices[i:i+self.slow_period]
            fast_ema_val = self._calculate_ema(period_prices, self.fast_period)
            slow_ema_val = self._calculate_ema(period_prices, self.slow_period)
            recent_macd_values.append(fast_ema_val - slow_ema_val)
        
        if len(recent_macd_values) < 2:
            return False
        
        # Find lows
        price_low = min(recent_prices)
        macd_low = min(recent_macd_values)
        
        # Get previous period data
        prev_prices = [data['price'] for data in self.price_history[symbol][-self.divergence_lookback*2:-self.divergence_lookback]]
        prev_macd_values = []
        
        for i in range(len(prev_prices) - self.slow_period + 1):
            period_prices = prev_prices[i:i+self.slow_period]
            fast_ema_val = self._calculate_ema(period_prices, self.fast_period)
            slow_ema_val = self._calculate_ema(period_prices, self.slow_period)
            prev_macd_values.append(fast_ema_val - slow_ema_val)
        
        if len(prev_macd_values) < 2:
            return False
        
        prev_price_low = min(prev_prices)
        prev_macd_low = min(prev_macd_values)
        
        # Check for bullish divergence
        return (price_low < prev_price_low and macd_low > prev_macd_low)
    
    def _check_bearish_divergence(self, symbol: str) -> bool:
        """Check for bearish divergence (price makes higher high, MACD makes lower high)"""
        if len(self.price_history[symbol]) < self.divergence_lookback * 2:
            return False
        
        # Get recent price and MACD data
        recent_prices = [data['price'] for data in self.price_history[symbol][-self.divergence_lookback:]]
        recent_macd_values = []
        
        # Calculate MACD for recent period
        for i in range(len(recent_prices) - self.slow_period + 1):
            period_prices = recent_prices[i:i+self.slow_period]
            fast_ema_val = self._calculate_ema(period_prices, self.fast_period)
            slow_ema_val = self._calculate_ema(period_prices, self.slow_period)
            recent_macd_values.append(fast_ema_val - slow_ema_val)
        
        if len(recent_macd_values) < 2:
            return False
        
        # Find highs
        price_high = max(recent_prices)
        macd_high = max(recent_macd_values)
        
        # Get previous period data
        prev_prices = [data['price'] for data in self.price_history[symbol][-self.divergence_lookback*2:-self.divergence_lookback]]
        prev_macd_values = []
        
        for i in range(len(prev_prices) - self.slow_period + 1):
            period_prices = prev_prices[i:i+self.slow_period]
            fast_ema_val = self._calculate_ema(period_prices, self.fast_period)
            slow_ema_val = self._calculate_ema(period_prices, self.slow_period)
            prev_macd_values.append(fast_ema_val - slow_ema_val)
        
        if len(prev_macd_values) < 2:
            return False
        
        prev_price_high = max(prev_prices)
        prev_macd_high = max(prev_macd_values)
        
        # Check for bearish divergence
        return (price_high > prev_price_high and macd_high < prev_macd_high)
    
    def get_strategy_indicators(self, symbol: str) -> Dict[str, float]:
        """Get current indicator values for a symbol"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < self.slow_period + self.signal_period:
            return {}
        
        self._calculate_macd(symbol)
        
        return {
            'macd': self.macd_line.get(symbol, 0),
            'signal': self.signal_line.get(symbol, 0),
            'histogram': self.histogram.get(symbol, 0),
            'fast_ema': self.fast_ema.get(symbol, 0),
            'slow_ema': self.slow_ema.get(symbol, 0),
            'current_price': self.price_history[symbol][-1]['price'] if self.price_history[symbol] else 0
        } 