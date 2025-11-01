"""
Bollinger Bands Strategy

This strategy implements Bollinger Bands-based trading signals:
- Generates BUY signals when price touches lower band
- Generates SELL signals when price touches upper band
- Includes squeeze detection and volatility analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import logging

from .base_strategy import BaseStrategy, StrategyConfig, Signal, Position

logger = logging.getLogger(__name__)

class BollingerBandsStrategy(BaseStrategy):
    """
    Bollinger Bands Strategy
    
    Parameters:
    - period: Moving average period (default: 20)
    - std_dev: Standard deviation multiplier (default: 2)
    - squeeze_threshold: Squeeze detection threshold (default: 0.1)
    - volume_confirmation: Require volume confirmation (default: True)
    - volatility_threshold: Minimum volatility for signal (default: 0.02)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy-specific parameters
        self.period = self.parameters.get('period', 20)
        self.std_dev = self.parameters.get('std_dev', 2)
        self.squeeze_threshold = self.parameters.get('squeeze_threshold', 0.1)
        self.volume_confirmation = self.parameters.get('volume_confirmation', True)
        self.volatility_threshold = self.parameters.get('volatility_threshold', 0.02)
        
        # Technical indicators storage
        self.middle_band = {}
        self.upper_band = {}
        self.lower_band = {}
        self.bandwidth = {}
        self.percent_b = {}
        self.squeeze = {}
        
        logger.info(f"Initialized Bollinger Bands Strategy with period={self.period}, std_dev={self.std_dev}")
    
    def _generate_signals(self):
        """Generate trading signals based on Bollinger Bands"""
        for symbol in self.symbols:
            if symbol not in self.price_history or len(self.price_history[symbol]) < self.period:
                continue
            
            # Calculate Bollinger Bands
            self._calculate_bollinger_bands(symbol)
            
            # Check for Bollinger Bands signals
            signal = self._check_bollinger_signal(symbol)
            
            if signal:
                self.add_signal(signal)
    
    def _calculate_bollinger_bands(self, symbol: str):
        """Calculate Bollinger Bands for a symbol"""
        if len(self.price_history[symbol]) < self.period:
            return
        
        prices = [data['price'] for data in self.price_history[symbol]]
        
        # Calculate middle band (SMA)
        middle_band = np.mean(prices[-self.period:])
        self.middle_band[symbol] = middle_band
        
        # Calculate standard deviation
        std_deviation = np.std(prices[-self.period:])
        
        # Calculate upper and lower bands
        upper_band = middle_band + (self.std_dev * std_deviation)
        lower_band = middle_band - (self.std_dev * std_deviation)
        
        self.upper_band[symbol] = upper_band
        self.lower_band[symbol] = lower_band
        
        # Calculate bandwidth (volatility measure)
        bandwidth = (upper_band - lower_band) / middle_band
        self.bandwidth[symbol] = bandwidth
        
        # Calculate %B (position within bands)
        current_price = prices[-1]
        percent_b = (current_price - lower_band) / (upper_band - lower_band)
        self.percent_b[symbol] = percent_b
        
        # Detect squeeze (low volatility)
        self.squeeze[symbol] = bandwidth < self.squeeze_threshold
    
    def _check_bollinger_signal(self, symbol: str) -> Optional[Signal]:
        """Check for Bollinger Bands-based trading signals"""
        if (symbol not in self.upper_band or symbol not in self.lower_band or 
            symbol not in self.middle_band):
            return None
        
        current_price = self.price_history[symbol][-1]['price']
        timestamp = self.price_history[symbol][-1]['timestamp']
        upper_band = self.upper_band[symbol]
        lower_band = self.lower_band[symbol]
        middle_band = self.middle_band[symbol]
        percent_b = self.percent_b[symbol]
        bandwidth = self.bandwidth[symbol]
        
        # Check volatility threshold
        if bandwidth < self.volatility_threshold:
            return None
        
        # Check volume confirmation if required
        if self.volume_confirmation:
            recent_volume = sum([data['volume'] for data in self.price_history[symbol][-5:]])
            avg_volume = np.mean([data['volume'] for data in self.price_history[symbol][-20:]])
            if recent_volume < avg_volume * 1.2:  # Require 20% above average volume
                return None
        
        # Get previous values for crossover detection
        if len(self.price_history[symbol]) < self.period + 1:
            return None
        
        prev_price = self.price_history[symbol][-2]['price']
        
        # Bullish signal (price touches lower band and starts moving up)
        if (prev_price <= lower_band and current_price > lower_band and 
            current_price < middle_band and percent_b < 0.3):
            
            confidence = min((middle_band - current_price) / (middle_band - lower_band), 1.0)
            
            return Signal(
                symbol=symbol,
                signal_type='BUY',
                price=current_price,
                timestamp=timestamp,
                confidence=confidence,
                strategy_name=self.strategy_name,
                additional_data={
                    'upper_band': upper_band,
                    'middle_band': middle_band,
                    'lower_band': lower_band,
                    'percent_b': percent_b,
                    'bandwidth': bandwidth,
                    'squeeze': self.squeeze[symbol]
                }
            )
        
        # Bearish signal (price touches upper band and starts moving down)
        elif (prev_price >= upper_band and current_price < upper_band and 
              current_price > middle_band and percent_b > 0.7):
            
            confidence = min((current_price - middle_band) / (upper_band - middle_band), 1.0)
            
            return Signal(
                symbol=symbol,
                signal_type='SELL',
                price=current_price,
                timestamp=timestamp,
                confidence=confidence,
                strategy_name=self.strategy_name,
                additional_data={
                    'upper_band': upper_band,
                    'middle_band': middle_band,
                    'lower_band': lower_band,
                    'percent_b': percent_b,
                    'bandwidth': bandwidth,
                    'squeeze': self.squeeze[symbol]
                }
            )
        
        # Squeeze breakout signals
        elif self.squeeze[symbol]:
            # Bullish breakout from squeeze
            if (percent_b > 0.8 and current_price > prev_price and 
                bandwidth > self.squeeze_threshold * 1.5):
                
                confidence = min(percent_b, 1.0)
                
                return Signal(
                    symbol=symbol,
                    signal_type='BUY',
                    price=current_price,
                    timestamp=timestamp,
                    confidence=confidence,
                    strategy_name=self.strategy_name,
                    additional_data={
                        'upper_band': upper_band,
                        'middle_band': middle_band,
                        'lower_band': lower_band,
                        'percent_b': percent_b,
                        'bandwidth': bandwidth,
                        'squeeze': self.squeeze[symbol],
                        'breakout_type': 'bullish'
                    }
                )
            
            # Bearish breakout from squeeze
            elif (percent_b < 0.2 and current_price < prev_price and 
                  bandwidth > self.squeeze_threshold * 1.5):
                
                confidence = min(1 - percent_b, 1.0)
                
                return Signal(
                    symbol=symbol,
                    signal_type='SELL',
                    price=current_price,
                    timestamp=timestamp,
                    confidence=confidence,
                    strategy_name=self.strategy_name,
                    additional_data={
                        'upper_band': upper_band,
                        'middle_band': middle_band,
                        'lower_band': lower_band,
                        'percent_b': percent_b,
                        'bandwidth': bandwidth,
                        'squeeze': self.squeeze[symbol],
                        'breakout_type': 'bearish'
                    }
                )
        
        return None
    
    def _calculate_volatility(self, symbol: str) -> float:
        """Calculate price volatility"""
        if len(self.price_history[symbol]) < self.period:
            return 0.0
        
        prices = [data['price'] for data in self.price_history[symbol][-self.period:]]
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns)
        
        return volatility
    
    def _detect_squeeze(self, symbol: str) -> bool:
        """Detect Bollinger Bands squeeze (low volatility)"""
        if symbol not in self.bandwidth:
            return False
        
        return self.bandwidth[symbol] < self.squeeze_threshold
    
    def get_strategy_indicators(self, symbol: str) -> Dict[str, float]:
        """Get current indicator values for a symbol"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < self.period:
            return {}
        
        self._calculate_bollinger_bands(symbol)
        
        return {
            'upper_band': self.upper_band.get(symbol, 0),
            'middle_band': self.middle_band.get(symbol, 0),
            'lower_band': self.lower_band.get(symbol, 0),
            'percent_b': self.percent_b.get(symbol, 0.5),
            'bandwidth': self.bandwidth.get(symbol, 0),
            'squeeze': self.squeeze.get(symbol, False),
            'volatility': self._calculate_volatility(symbol),
            'current_price': self.price_history[symbol][-1]['price'] if self.price_history[symbol] else 0
        } 