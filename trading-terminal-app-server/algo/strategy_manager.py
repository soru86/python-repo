"""
Strategy Manager for Algorithmic Trading

This module provides the main orchestration service for managing
all trading strategy containers and their lifecycle.
"""

import os
import json
import time
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
import signal
import sys

from .containers import ContainerManager, ManagerConfig
from .containers.strategy_container import ContainerConfig
from .redis_streams import streams_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StrategyManager:
    """
    Main strategy manager for orchestrating algorithmic trading containers
    
    This class provides:
    - Container lifecycle management
    - Strategy deployment and configuration
    - Health monitoring and auto-recovery
    - Performance metrics aggregation
    - API endpoints for management
    """
    
    def __init__(self):
        # Load configuration from environment
        self.config = self._load_manager_config()
        
        # Initialize container manager
        self.container_manager = ContainerManager(self.config)
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Management state
        self.running = False
        self.monitoring_thread = None
        
        logger.info("Strategy manager initialized")
    
    def _load_manager_config(self) -> ManagerConfig:
        """Load manager configuration from environment variables"""
        return ManagerConfig(
            max_containers=int(os.getenv('MAX_CONTAINERS', 10)),
            max_memory_per_container=os.getenv('MAX_MEMORY_PER_CONTAINER', '512m'),
            max_cpu_per_container=os.getenv('MAX_CPU_PER_CONTAINER', '0.5'),
            health_check_interval=int(os.getenv('HEALTH_CHECK_INTERVAL', 30)),
            auto_restart_failed=os.getenv('AUTO_RESTART_FAILED', 'true').lower() == 'true',
            redis_host=os.getenv('REDIS_HOST', 'redis'),
            redis_port=int(os.getenv('REDIS_PORT', 6379))
        )
    
    def start(self):
        """Start the strategy manager"""
        try:
            logger.info("Starting strategy manager...")
            
            # Test Redis connection
            if not streams_manager.redis_client.ping():
                logger.error("Cannot connect to Redis")
                return False
            
            # Start container manager
            self.container_manager.start()
            
            # Start monitoring thread
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            self.running = True
            logger.info("Strategy manager started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting strategy manager: {e}")
            return False
    
    def stop(self):
        """Stop the strategy manager"""
        try:
            logger.info("Stopping strategy manager...")
            self.running = False
            
            # Stop container manager
            self.container_manager.stop()
            
            logger.info("Strategy manager stopped")
            
        except Exception as e:
            logger.error(f"Error stopping strategy manager: {e}")
    
    def deploy_strategy(self, strategy_config: Dict[str, Any]) -> bool:
        """
        Deploy a new trading strategy
        
        Args:
            strategy_config: Strategy configuration dictionary
            
        Returns:
            bool: True if deployment successful, False otherwise
        """
        try:
            # Convert dict to ContainerConfig
            container_config = ContainerConfig(
                strategy_name=strategy_config['strategy_name'],
                strategy_type=strategy_config['strategy_type'],
                symbols=strategy_config['symbols'],
                exchange=strategy_config['exchange'],
                parameters=strategy_config.get('parameters', {}),
                risk_management=strategy_config.get('risk_management', {}),
                redis_host=self.config.redis_host,
                redis_port=self.config.redis_port
            )
            
            return self.container_manager.deploy_strategy(container_config)
            
        except Exception as e:
            logger.error(f"Error deploying strategy: {e}")
            return False
    
    def get_all_strategies(self) -> Dict[str, Any]:
        """Get status of all strategies"""
        try:
            return {
                'strategies': self.container_manager.get_all_status(),
                'performance_metrics': self.container_manager.get_performance_metrics(),
                'manager_status': {
                    'running': self.running,
                    'max_containers': self.config.max_containers,
                    'current_containers': len(self.container_manager.containers)
                }
            }
        except Exception as e:
            logger.error(f"Error getting all strategies: {e}")
            return {}
    
    def get_strategy_logs(self, strategy_name: str, tail: int = 100) -> List[str]:
        """Get logs for a specific strategy"""
        try:
            return self.container_manager.get_strategy_logs(strategy_name, tail)
        except Exception as e:
            logger.error(f"Error getting logs for strategy {strategy_name}: {e}")
            return []
    
    def restart_strategy(self, strategy_name: str) -> bool:
        """Restart a specific strategy"""
        try:
            return self.container_manager.restart_strategy(strategy_name)
        except Exception as e:
            logger.error(f"Error restarting strategy {strategy_name}: {e}")
            return False
    
    def stop_strategy(self, strategy_name: str) -> bool:
        """Stop a specific strategy"""
        try:
            return self.container_manager.stop_strategy(strategy_name)
        except Exception as e:
            logger.error(f"Error stopping strategy {strategy_name}: {e}")
            return False
    
    def _monitoring_loop(self):
        """Main monitoring loop for strategy manager"""
        while self.running:
            try:
                # Check Redis connection
                if not streams_manager.redis_client.ping():
                    logger.warning("Redis connection lost, attempting to reconnect...")
                    time.sleep(5)
                    continue
                
                # Get performance metrics
                metrics = self.container_manager.get_performance_metrics()
                
                # Log performance summary
                if metrics:
                    logger.info(f"Performance Summary: {metrics['running_containers']}/{metrics['total_containers']} containers running, "
                              f"Memory: {metrics.get('total_memory_usage_mb', 0):.1f}MB, "
                              f"CPU: {metrics.get('total_cpu_usage_percent', 0):.1f}%")
                
                # Sleep before next check
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the strategy manager"""
        try:
            return {
                'status': 'healthy' if self.running else 'unhealthy',
                'running': self.running,
                'redis_connected': streams_manager.redis_client.ping(),
                'container_manager_running': self.container_manager.running if hasattr(self.container_manager, 'running') else False,
                'active_strategies': len(self.container_manager.containers),
                'max_strategies': self.config.max_containers,
                'uptime': time.time() if self.running else 0
            }
        except Exception as e:
            logger.error(f"Error getting health status: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }

def main():
    """Main entry point for the strategy manager"""
    try:
        # Create and start strategy manager
        manager = StrategyManager()
        
        if manager.start():
            logger.info("Strategy manager started successfully")
            
            # Keep the process running
            while manager.running:
                time.sleep(1)
        else:
            logger.error("Failed to start strategy manager")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error in strategy manager: {e}")
        sys.exit(1)
    finally:
        if 'manager' in locals():
            manager.stop()

if __name__ == '__main__':
    main() 