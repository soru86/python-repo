"""
Strategy Runner for Docker Containers

This module runs inside Docker containers and executes trading strategies
using Redis Streams for market data. It's the main entry point for
strategy containers.
"""

import os
import json
import time
import logging
import signal
import sys
from typing import Dict, Any
from datetime import datetime

from strategies import (
    MovingAverageStrategy, 
    RSIStrategy, 
    MACDStrategy, 
    BollingerBandsStrategy
)
from strategies.base_strategy import StrategyConfig
from redis_streams import streams_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StrategyRunner:
    """
    Main strategy runner for Docker containers
    
    This class:
    - Loads strategy configuration from environment variables
    - Initializes the appropriate strategy
    - Manages the strategy lifecycle
    - Handles graceful shutdown
    """
    
    def __init__(self):
        self.strategy = None
        self.running = False
        
        # Load configuration from environment
        self.config = self._load_config()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _load_config(self) -> StrategyConfig:
        """Load strategy configuration from environment variables"""
        try:
            strategy_name = os.getenv('STRATEGY_NAME', 'default_strategy')
            strategy_type = os.getenv('STRATEGY_TYPE', 'moving_average')
            symbols = json.loads(os.getenv('SYMBOLS', '["BTCUSDT"]'))
            exchange = os.getenv('EXCHANGE', 'binance')
            parameters = json.loads(os.getenv('PARAMETERS', '{}'))
            risk_management = json.loads(os.getenv('RISK_MANAGEMENT', '{}'))
            
            # Set default parameters based on strategy type
            if not parameters:
                parameters = self._get_default_parameters(strategy_type)
            
            # Set default risk management
            if not risk_management:
                risk_management = {
                    'stop_loss_pct': 0.02,
                    'take_profit_pct': 0.05,
                    'max_position_size': 0.1,
                    'max_daily_loss': 0.05
                }
            
            return StrategyConfig(
                strategy_name=strategy_name,
                symbols=symbols,
                exchange=exchange,
                timeframe='1m',
                parameters=parameters,
                risk_management=risk_management,
                enabled=True
            )
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            # Return minimal default config
            return StrategyConfig(
                strategy_name='default_strategy',
                symbols=['BTCUSDT'],
                exchange='binance',
                timeframe='1m',
                parameters={},
                risk_management={},
                enabled=True
            )
    
    def _get_default_parameters(self, strategy_type: str) -> Dict[str, Any]:
        """Get default parameters for strategy type"""
        defaults = {
            'moving_average': {
                'fast_period': 10,
                'slow_period': 20,
                'min_trend_strength': 0.1,
                'volume_threshold': 1000
            },
            'rsi': {
                'rsi_period': 14,
                'oversold_level': 30,
                'overbought_level': 70,
                'divergence_lookback': 10,
                'momentum_threshold': 0.5
            },
            'macd': {
                'fast_period': 12,
                'slow_period': 26,
                'signal_period': 9,
                'histogram_threshold': 0.001,
                'divergence_lookback': 20
            },
            'bollinger_bands': {
                'period': 20,
                'std_dev': 2,
                'squeeze_threshold': 0.1,
                'volume_confirmation': True,
                'volatility_threshold': 0.02
            }
        }
        
        return defaults.get(strategy_type, {})
    
    def _create_strategy(self) -> bool:
        """Create and initialize the strategy"""
        try:
            strategy_type = os.getenv('STRATEGY_TYPE', 'moving_average')
            
            if strategy_type == 'moving_average':
                self.strategy = MovingAverageStrategy(self.config)
            elif strategy_type == 'rsi':
                self.strategy = RSIStrategy(self.config)
            elif strategy_type == 'macd':
                self.strategy = MACDStrategy(self.config)
            elif strategy_type == 'bollinger_bands':
                self.strategy = BollingerBandsStrategy(self.config)
            else:
                logger.error(f"Unknown strategy type: {strategy_type}")
                return False
            
            logger.info(f"Created strategy: {self.config.strategy_name} ({strategy_type})")
            return True
            
        except Exception as e:
            logger.error(f"Error creating strategy: {e}")
            return False
    
    def start(self):
        """Start the strategy runner"""
        try:
            logger.info("Starting strategy runner...")
            
            # Create strategy
            if not self._create_strategy():
                logger.error("Failed to create strategy")
                return False
            
            # Test Redis connection
            if not streams_manager.redis_client.ping():
                logger.error("Cannot connect to Redis")
                return False
            
            logger.info("Strategy runner started successfully")
            self.running = True
            
            # Start strategy execution
            self.strategy.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting strategy runner: {e}")
            return False
    
    def stop(self):
        """Stop the strategy runner"""
        try:
            logger.info("Stopping strategy runner...")
            self.running = False
            
            if self.strategy:
                self.strategy.stop()
            
            logger.info("Strategy runner stopped")
            
        except Exception as e:
            logger.error(f"Error stopping strategy runner: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the strategy runner"""
        try:
            if not self.strategy:
                return {
                    'status': 'not_initialized',
                    'strategy_name': self.config.strategy_name,
                    'strategy_type': os.getenv('STRATEGY_TYPE', 'unknown'),
                    'symbols': self.config.symbols,
                    'running': False
                }
            
            # Get strategy performance metrics
            metrics = self.strategy.get_performance_metrics()
            position_summary = self.strategy.get_position_summary()
            
            return {
                'status': 'running' if self.running else 'stopped',
                'strategy_name': self.config.strategy_name,
                'strategy_type': os.getenv('STRATEGY_TYPE', 'unknown'),
                'symbols': self.config.symbols,
                'running': self.running,
                'performance_metrics': metrics,
                'position_summary': position_summary,
                'redis_connected': streams_manager.redis_client.ping()
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

def main():
    """Main entry point for the strategy runner"""
    try:
        # Create and start strategy runner
        runner = StrategyRunner()
        
        if runner.start():
            logger.info("Strategy runner started successfully")
            
            # Keep the process running
            while runner.running:
                time.sleep(1)
        else:
            logger.error("Failed to start strategy runner")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error in strategy runner: {e}")
        sys.exit(1)
    finally:
        if 'runner' in locals():
            runner.stop()

if __name__ == '__main__':
    main() 