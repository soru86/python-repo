"""
RSI (Relative Strength Index) Strategy

This strategy implements RSI-based trading signals:
- Generates BUY signals when RSI crosses above oversold level (30)
- Generates SELL signals when RSI crosses below overbought level (70)
- Includes divergence detection and momentum confirmation
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import logging

from .base_strategy import BaseStrategy, StrategyConfig, Signal, Position

logger = logging.getLogger(__name__)

class RSIStrategy(BaseStrategy):
    """
    RSI (Relative Strength Index) Strategy
    
    Parameters:
    - rsi_period: RSI calculation period (default: 14)
    - oversold_level: Oversold threshold (default: 30)
    - overbought_level: Overbought threshold (default: 70)
    - divergence_lookback: Periods to look back for divergence (default: 10)
    - momentum_threshold: Minimum momentum for signal confirmation (default: 0.5)
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy-specific parameters
        self.rsi_period = self.parameters.get('rsi_period', 14)
        self.oversold_level = self.parameters.get('oversold_level', 30)
        self.overbought_level = self.parameters.get('overbought_level', 70)
        self.divergence_lookback = self.parameters.get('divergence_lookback', 10)
        self.momentum_threshold = self.parameters.get('momentum_threshold', 0.5)
        
        # Technical indicators storage
        self.rsi_values = {}
        self.price_highs = {}
        self.price_lows = {}
        self.rsi_highs = {}
        self.rsi_lows = {}
        
        logger.info(f"Initialized RSI Strategy with period={self.rsi_period}, oversold={self.oversold_level}, overbought={self.overbought_level}")
    
    def _generate_signals(self):
        """Generate trading signals based on RSI levels and divergence"""
        for symbol in self.symbols:
            if symbol not in self.price_history or len(self.price_history[symbol]) < self.rsi_period + 1:
                continue
            
            # Calculate RSI
            self._calculate_rsi(symbol)
            
            # Check for RSI signals
            signal = self._check_rsi_signal(symbol)
            
            if signal:
                self.add_signal(signal)
    
    def _calculate_rsi(self, symbol: str):
        """Calculate RSI for a symbol"""
        if len(self.price_history[symbol]) < self.rsi_period + 1:
            return
        
        prices = [data['price'] for data in self.price_history[symbol]]
        
        # Calculate price changes
        price_changes = np.diff(prices)
        
        # Separate gains and losses
        gains = np.where(price_changes > 0, price_changes, 0)
        losses = np.where(price_changes < 0, -price_changes, 0)
        
        # Calculate average gains and losses
        avg_gains = np.mean(gains[-self.rsi_period:])
        avg_losses = np.mean(losses[-self.rsi_period:])
        
        # Calculate RSI
        if avg_losses == 0:
            rsi = 100
        else:
            rs = avg_gains / avg_losses
            rsi = 100 - (100 / (1 + rs))
        
        self.rsi_values[symbol] = rsi
        
        # Track highs and lows for divergence detection
        self._update_highs_lows(symbol)
    
    def _update_highs_lows(self, symbol: str):
        """Update price and RSI highs/lows for divergence detection"""
        if len(self.price_history[symbol]) < self.divergence_lookback:
            return
        
        prices = [data['price'] for data in self.price_history[symbol][-self.divergence_lookback:]]
        rsi_values = []
        
        # Calculate RSI for each point in lookback period
        for i in range(len(prices) - self.rsi_period):
            period_prices = prices[i:i+self.rsi_period+1]
            price_changes = np.diff(period_prices)
            gains = np.where(price_changes > 0, price_changes, 0)
            losses = np.where(price_changes < 0, -price_changes, 0)
            
            avg_gains = np.mean(gains)
            avg_losses = np.mean(losses)
            
            if avg_losses == 0:
                rsi = 100
            else:
                rs = avg_gains / avg_losses
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append(rsi)
        
        # Find highs and lows
        if len(prices) >= 2:
            price_high = max(prices)
            price_low = min(prices)
            self.price_highs[symbol] = price_high
            self.price_lows[symbol] = price_low
        
        if len(rsi_values) >= 2:
            rsi_high = max(rsi_values)
            rsi_low = min(rsi_values)
            self.rsi_highs[symbol] = rsi_high
            self.rsi_lows[symbol] = rsi_low
    
    def _check_rsi_signal(self, symbol: str) -> Optional[Signal]:
        """Check for RSI-based trading signals"""
        if symbol not in self.rsi_values:
            return None
        
        current_rsi = self.rsi_values[symbol]
        current_price = self.price_history[symbol][-1]['price']
        timestamp = self.price_history[symbol][-1]['timestamp']
        
        # Get previous RSI for crossover detection
        if len(self.price_history[symbol]) < self.rsi_period + 2:
            return None
        
        prev_prices = [data['price'] for data in self.price_history[symbol][-self.rsi_period-2:-1]]
        prev_price_changes = np.diff(prev_prices)
        prev_gains = np.where(prev_price_changes > 0, prev_price_changes, 0)
        prev_losses = np.where(prev_price_changes < 0, -prev_price_changes, 0)
        
        prev_avg_gains = np.mean(prev_gains)
        prev_avg_losses = np.mean(prev_losses)
        
        if prev_avg_losses == 0:
            prev_rsi = 100
        else:
            prev_rs = prev_avg_gains / prev_avg_losses
            prev_rsi = 100 - (100 / (1 + prev_rs))
        
        # Calculate momentum
        momentum = abs(current_rsi - prev_rsi)
        
        # Check for oversold condition (BUY signal)
        if (prev_rsi <= self.oversold_level and current_rsi > self.oversold_level and 
            momentum >= self.momentum_threshold):
            
            confidence = min((current_rsi - self.oversold_level) / (50 - self.oversold_level), 1.0)
            
            return Signal(
                symbol=symbol,
                signal_type='BUY',
                price=current_price,
                timestamp=timestamp,
                confidence=confidence,
                strategy_name=self.strategy_name,
                additional_data={
                    'rsi': current_rsi,
                    'momentum': momentum,
                    'divergence': self._check_bullish_divergence(symbol)
                }
            )
        
        # Check for overbought condition (SELL signal)
        elif (prev_rsi >= self.overbought_level and current_rsi < self.overbought_level and 
              momentum >= self.momentum_threshold):
            
            confidence = min((self.overbought_level - current_rsi) / (self.overbought_level - 50), 1.0)
            
            return Signal(
                symbol=symbol,
                signal_type='SELL',
                price=current_price,
                timestamp=timestamp,
                confidence=confidence,
                strategy_name=self.strategy_name,
                additional_data={
                    'rsi': current_rsi,
                    'momentum': momentum,
                    'divergence': self._check_bearish_divergence(symbol)
                }
            )
        
        return None
    
    def _check_bullish_divergence(self, symbol: str) -> bool:
        """Check for bullish divergence (price makes lower low, RSI makes higher low)"""
        if (symbol not in self.price_lows or symbol not in self.rsi_lows or 
            len(self.price_history[symbol]) < self.divergence_lookback * 2):
            return False
        
        # Compare current lows with previous lows
        current_price_low = self.price_lows[symbol]
        current_rsi_low = self.rsi_lows[symbol]
        
        # Get previous period data
        prev_prices = [data['price'] for data in self.price_history[symbol][-self.divergence_lookback*2:-self.divergence_lookback]]
        prev_price_low = min(prev_prices) if prev_prices else 0
        
        # Calculate previous RSI
        if len(prev_prices) >= self.rsi_period + 1:
            prev_price_changes = np.diff(prev_prices)
            prev_gains = np.where(prev_price_changes > 0, prev_price_changes, 0)
            prev_losses = np.where(prev_price_changes < 0, -prev_price_changes, 0)
            
            prev_avg_gains = np.mean(prev_gains)
            prev_avg_losses = np.mean(prev_losses)
            
            if prev_avg_losses == 0:
                prev_rsi_low = 100
            else:
                prev_rs = prev_avg_gains / prev_avg_losses
                prev_rsi_low = 100 - (100 / (1 + prev_rs))
            
            # Check for bullish divergence
            return (current_price_low < prev_price_low and current_rsi_low > prev_rsi_low)
        
        return False
    
    def _check_bearish_divergence(self, symbol: str) -> bool:
        """Check for bearish divergence (price makes higher high, RSI makes lower high)"""
        if (symbol not in self.price_highs or symbol not in self.rsi_highs or 
            len(self.price_history[symbol]) < self.divergence_lookback * 2):
            return False
        
        # Compare current highs with previous highs
        current_price_high = self.price_highs[symbol]
        current_rsi_high = self.rsi_highs[symbol]
        
        # Get previous period data
        prev_prices = [data['price'] for data in self.price_history[symbol][-self.divergence_lookback*2:-self.divergence_lookback]]
        prev_price_high = max(prev_prices) if prev_prices else 0
        
        # Calculate previous RSI
        if len(prev_prices) >= self.rsi_period + 1:
            prev_price_changes = np.diff(prev_prices)
            prev_gains = np.where(prev_price_changes > 0, prev_price_changes, 0)
            prev_losses = np.where(prev_price_changes < 0, -prev_price_changes, 0)
            
            prev_avg_gains = np.mean(prev_gains)
            prev_avg_losses = np.mean(prev_losses)
            
            if prev_avg_losses == 0:
                prev_rsi_high = 100
            else:
                prev_rs = prev_avg_gains / prev_avg_losses
                prev_rsi_high = 100 - (100 / (1 + prev_rs))
            
            # Check for bearish divergence
            return (current_price_high > prev_price_high and current_rsi_high < prev_rsi_high)
        
        return False
    
    def get_strategy_indicators(self, symbol: str) -> Dict[str, float]:
        """Get current indicator values for a symbol"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < self.rsi_period + 1:
            return {}
        
        self._calculate_rsi(symbol)
        
        return {
            'rsi': self.rsi_values.get(symbol, 50),
            'oversold_level': self.oversold_level,
            'overbought_level': self.overbought_level,
            'current_price': self.price_history[symbol][-1]['price'] if self.price_history[symbol] else 0
        } 