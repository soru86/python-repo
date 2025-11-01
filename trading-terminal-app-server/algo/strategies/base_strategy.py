"""
Base Strategy Class for Algorithmic Trading

This module provides the foundation for all trading strategies.
Each strategy container will inherit from this base class and implement
specific trading logic while using Redis Streams for market data.
"""

import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
import pandas as pd

from ..redis_streams import streams_manager, MarketData

logger = logging.getLogger(__name__)

@dataclass
class Signal:
    """Trading signal structure"""
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    price: float
    timestamp: int
    confidence: float  # 0.0 to 1.0
    strategy_name: str
    additional_data: Dict[str, Any] = None

@dataclass
class Position:
    """Position tracking structure"""
    symbol: str
    side: str  # 'LONG', 'SHORT'
    quantity: float
    entry_price: float
    entry_time: int
    current_price: float = 0.0
    pnl: float = 0.0
    status: str = 'OPEN'  # 'OPEN', 'CLOSED'

@dataclass
class StrategyConfig:
    """Strategy configuration structure"""
    strategy_name: str
    symbols: List[str]
    exchange: str
    timeframe: str  # '1m', '5m', '15m', '1h', '1d'
    parameters: Dict[str, Any]
    risk_management: Dict[str, Any]
    enabled: bool = True

class BaseStrategy(ABC):
    """
    Base class for all trading strategies
    
    This class provides:
    - Redis Streams integration for market data
    - Signal generation and management
    - Position tracking
    - Risk management utilities
    - Performance metrics
    """
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.strategy_name = config.strategy_name
        self.symbols = config.symbols
        self.exchange = config.exchange
        self.timeframe = config.timeframe
        self.parameters = config.parameters
        self.risk_management = config.risk_management
        
        # Market data storage
        self.market_data = {}
        self.price_history = {}
        
        # Signal and position tracking
        self.signals = []
        self.positions = {}
        self.closed_positions = []
        
        # Performance metrics
        self.total_pnl = 0.0
        self.win_count = 0
        self.loss_count = 0
        self.total_trades = 0
        
        # Redis Streams setup
        self.stream_keys = {}
        self.consumer_groups = {}
        self._setup_streams()
        
        logger.info(f"Initialized strategy: {self.strategy_name}")
    
    def _setup_streams(self):
        """Setup Redis Streams for each symbol"""
        for symbol in self.symbols:
            stream_key = streams_manager.create_stream_key(
                self.exchange, symbol, "tick"
            )
            self.stream_keys[symbol] = stream_key
            
            # Create consumer group for this strategy
            group_name = f"{self.strategy_name}_{symbol}"
            self.consumer_groups[symbol] = group_name
            
            # Initialize price history
            self.price_history[symbol] = []
    
    def start(self):
        """Start the strategy execution"""
        logger.info(f"Starting strategy: {self.strategy_name}")
        
        while self.config.enabled:
            try:
                # Process market data for each symbol
                for symbol in self.symbols:
                    self._process_symbol_data(symbol)
                
                # Update positions and calculate PnL
                self._update_positions()
                
                # Generate signals based on strategy logic
                self._generate_signals()
                
                # Risk management checks
                self._risk_management_checks()
                
                # Sleep to avoid excessive CPU usage
                time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info(f"Stopping strategy: {self.strategy_name}")
                break
            except Exception as e:
                logger.error(f"Error in strategy execution: {e}")
                time.sleep(5)  # Wait before retrying
    
    def _process_symbol_data(self, symbol: str):
        """Process market data for a specific symbol"""
        try:
            stream_key = self.stream_keys[symbol]
            group_name = self.consumer_groups[symbol]
            consumer_name = f"{self.strategy_name}_consumer"
            
            # Read market data from Redis Stream
            messages = streams_manager.read_market_data(
                stream_key, group_name, consumer_name, count=10, block_ms=1000
            )
            
            for message_id, data in messages:
                # Process the market data
                market_data = MarketData(
                    symbol=data['symbol'],
                    price=float(data['price']),
                    volume=float(data['volume']),
                    timestamp=int(data['timestamp']),
                    exchange=data['exchange'],
                    data_type=data['data_type'],
                    additional_data=data.get('additional_data', {})
                )
                
                # Update price history
                self._update_price_history(symbol, market_data)
                
                # Acknowledge the message
                streams_manager.acknowledge_message(stream_key, group_name, message_id)
                
        except Exception as e:
            logger.error(f"Error processing data for {symbol}: {e}")
    
    def _update_price_history(self, symbol: str, market_data: MarketData):
        """Update price history for a symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        # Add new price data
        price_data = {
            'timestamp': market_data.timestamp,
            'price': market_data.price,
            'volume': market_data.volume
        }
        
        self.price_history[symbol].append(price_data)
        
        # Keep only recent data (e.g., last 1000 ticks)
        max_history = self.parameters.get('max_price_history', 1000)
        if len(self.price_history[symbol]) > max_history:
            self.price_history[symbol] = self.price_history[symbol][-max_history:]
    
    def _update_positions(self):
        """Update current positions with latest prices"""
        for symbol, position in self.positions.items():
            if position.status == 'OPEN' and symbol in self.price_history:
                # Get latest price
                if self.price_history[symbol]:
                    latest_price = self.price_history[symbol][-1]['price']
                    position.current_price = latest_price
                    
                    # Calculate PnL
                    if position.side == 'LONG':
                        position.pnl = (latest_price - position.entry_price) * position.quantity
                    else:  # SHORT
                        position.pnl = (position.entry_price - latest_price) * position.quantity
    
    @abstractmethod
    def _generate_signals(self):
        """
        Generate trading signals based on strategy logic
        
        This method must be implemented by each strategy subclass.
        It should analyze market data and generate appropriate signals.
        """
        pass
    
    def _risk_management_checks(self):
        """Perform risk management checks"""
        for symbol, position in list(self.positions.items()):
            if position.status == 'OPEN':
                # Check stop loss
                stop_loss = self.risk_management.get('stop_loss_pct', 0.02)
                if position.side == 'LONG':
                    loss_pct = (position.entry_price - position.current_price) / position.entry_price
                else:
                    loss_pct = (position.current_price - position.entry_price) / position.entry_price
                
                if loss_pct >= stop_loss:
                    self._close_position(symbol, "Stop Loss")
                
                # Check take profit
                take_profit = self.risk_management.get('take_profit_pct', 0.05)
                if position.side == 'LONG':
                    profit_pct = (position.current_price - position.entry_price) / position.entry_price
                else:
                    profit_pct = (position.entry_price - position.current_price) / position.entry_price
                
                if profit_pct >= take_profit:
                    self._close_position(symbol, "Take Profit")
    
    def _close_position(self, symbol: str, reason: str):
        """Close a position"""
        if symbol in self.positions:
            position = self.positions[symbol]
            position.status = 'CLOSED'
            
            # Move to closed positions
            self.closed_positions.append(position)
            del self.positions[symbol]
            
            # Update performance metrics
            self.total_pnl += position.pnl
            self.total_trades += 1
            
            if position.pnl > 0:
                self.win_count += 1
            else:
                self.loss_count += 1
            
            logger.info(f"Closed position for {symbol}: {reason}, PnL: {position.pnl}")
    
    def add_signal(self, signal: Signal):
        """Add a trading signal"""
        self.signals.append(signal)
        logger.info(f"Generated signal: {signal.signal_type} {signal.symbol} at {signal.price}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get strategy performance metrics"""
        win_rate = self.win_count / max(self.total_trades, 1)
        
        return {
            'strategy_name': self.strategy_name,
            'total_pnl': self.total_pnl,
            'total_trades': self.total_trades,
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'win_rate': win_rate,
            'open_positions': len(self.positions),
            'closed_positions': len(self.closed_positions)
        }
    
    def get_position_summary(self) -> Dict[str, Any]:
        """Get current position summary"""
        return {
            'open_positions': [asdict(pos) for pos in self.positions.values()],
            'closed_positions': [asdict(pos) for pos in self.closed_positions[-10:]]  # Last 10
        }
    
    def update_config(self, new_config: StrategyConfig):
        """Update strategy configuration"""
        self.config = new_config
        self.parameters = new_config.parameters
        self.risk_management = new_config.risk_management
        logger.info(f"Updated configuration for strategy: {self.strategy_name}")
    
    def stop(self):
        """Stop the strategy"""
        self.config.enabled = False
        logger.info(f"Stopped strategy: {self.strategy_name}") 