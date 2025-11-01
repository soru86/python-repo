"""
Container Manager for Algorithmic Trading Orchestration

This module manages multiple strategy containers, providing:
- Container lifecycle management
- Load balancing and resource allocation
- Health monitoring and auto-recovery
- Performance metrics aggregation
"""

import json
import time
import logging
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import docker
from docker.errors import DockerException

from .strategy_container import StrategyContainer, ContainerConfig

logger = logging.getLogger(__name__)

@dataclass
class ManagerConfig:
    """Container manager configuration"""
    max_containers: int = 10
    max_memory_per_container: str = '512m'
    max_cpu_per_container: str = '0.5'
    health_check_interval: int = 30  # seconds
    auto_restart_failed: bool = True
    redis_host: str = 'redis'
    redis_port: int = 6379

class ContainerManager:
    """
    Manages multiple strategy containers with Redis Streams integration
    
    This class provides:
    - Container orchestration and load balancing
    - Health monitoring and auto-recovery
    - Resource allocation and limits
    - Performance metrics aggregation
    - Strategy deployment and management
    """
    
    def __init__(self, config: ManagerConfig):
        self.config = config
        self.containers: Dict[str, StrategyContainer] = {}
        self.docker_client = None
        self.health_check_thread = None
        self.running = False
        
        # Try to initialize Docker client, but don't fail if not available
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.warning(f"Docker not available: {e}. Running in simulation mode.")
            self.docker_client = None
        
        logger.info(f"Initialized container manager with max_containers={config.max_containers}")
    
    def start(self):
        """Start the container manager"""
        self.running = True
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
        
        logger.info("Container manager started")
    
    def stop(self):
        """Stop the container manager"""
        self.running = False
        
        # Stop all containers
        for container in self.containers.values():
            container.stop()
        
        logger.info("Container manager stopped")
    
    def deploy_strategy(self, strategy_config: ContainerConfig) -> bool:
        """
        Deploy a new strategy container
        
        Args:
            strategy_config: Container configuration for the strategy
            
        Returns:
            bool: True if deployment successful, False otherwise
        """
        try:
            # Check resource limits
            if len(self.containers) >= self.config.max_containers:
                logger.error(f"Cannot deploy strategy: max containers ({self.config.max_containers}) reached")
                return False
            
            # Check if strategy already exists
            if strategy_config.strategy_name in self.containers:
                logger.warning(f"Strategy {strategy_config.strategy_name} already exists, updating...")
                return self.update_strategy(strategy_config)
            
            # Create and start container
            container = StrategyContainer(strategy_config)
            if container.start():
                self.containers[strategy_config.strategy_name] = container
                logger.info(f"Successfully deployed strategy: {strategy_config.strategy_name}")
                return True
            else:
                logger.error(f"Failed to start container for strategy: {strategy_config.strategy_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error deploying strategy {strategy_config.strategy_name}: {e}")
            return False
    
    def update_strategy(self, strategy_config: ContainerConfig) -> bool:
        """
        Update an existing strategy configuration
        
        Args:
            strategy_config: Updated container configuration
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            if strategy_config.strategy_name not in self.containers:
                logger.error(f"Strategy {strategy_config.strategy_name} not found")
                return False
            
            container = self.containers[strategy_config.strategy_name]
            return container.update_config(strategy_config)
            
        except Exception as e:
            logger.error(f"Error updating strategy {strategy_config.strategy_name}: {e}")
            return False
    
    def stop_strategy(self, strategy_name: str) -> bool:
        """
        Stop a specific strategy container
        
        Args:
            strategy_name: Name of the strategy to stop
            
        Returns:
            bool: True if stop successful, False otherwise
        """
        try:
            if strategy_name not in self.containers:
                logger.error(f"Strategy {strategy_name} not found")
                return False
            
            container = self.containers[strategy_name]
            if container.stop():
                del self.containers[strategy_name]
                logger.info(f"Stopped strategy: {strategy_name}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error stopping strategy {strategy_name}: {e}")
            return False
    
    def restart_strategy(self, strategy_name: str) -> bool:
        """
        Restart a specific strategy container
        
        Args:
            strategy_name: Name of the strategy to restart
            
        Returns:
            bool: True if restart successful, False otherwise
        """
        try:
            if strategy_name not in self.containers:
                logger.error(f"Strategy {strategy_name} not found")
                return False
            
            container = self.containers[strategy_name]
            return container.restart()
            
        except Exception as e:
            logger.error(f"Error restarting strategy {strategy_name}: {e}")
            return False
    
    def get_strategy_status(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific strategy
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            Dict containing strategy status or None if not found
        """
        try:
            if strategy_name not in self.containers:
                return None
            
            container = self.containers[strategy_name]
            return container.get_status()
            
        except Exception as e:
            logger.error(f"Error getting status for strategy {strategy_name}: {e}")
            return None
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all strategies
        
        Returns:
            Dict mapping strategy names to their status
        """
        try:
            status = {}
            for strategy_name, container in self.containers.items():
                status[strategy_name] = container.get_status()
            return status
            
        except Exception as e:
            logger.error(f"Error getting all strategy status: {e}")
            return {}
    
    def get_strategy_logs(self, strategy_name: str, tail: int = 100) -> List[str]:
        """
        Get logs for a specific strategy
        
        Args:
            strategy_name: Name of the strategy
            tail: Number of log lines to retrieve
            
        Returns:
            List of log lines
        """
        try:
            if strategy_name not in self.containers:
                return []
            
            container = self.containers[strategy_name]
            return container.get_logs(tail)
            
        except Exception as e:
            logger.error(f"Error getting logs for strategy {strategy_name}: {e}")
            return []
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated performance metrics for all strategies
        
        Returns:
            Dict containing aggregated metrics
        """
        try:
            total_containers = len(self.containers)
            running_containers = sum(1 for c in self.containers.values() if c.get_status()['running'])
            
            total_memory = 0
            total_cpu = 0
            strategy_types = {}
            
            for container in self.containers.values():
                status = container.get_status()
                if status['memory_usage']:
                    total_memory += status['memory_usage']
                if status['cpu_usage']:
                    total_cpu += status['cpu_usage']
                
                strategy_type = status.get('strategy_type', 'unknown')
                strategy_types[strategy_type] = strategy_types.get(strategy_type, 0) + 1
            
            return {
                'total_containers': total_containers,
                'running_containers': running_containers,
                'total_memory_usage_mb': total_memory,
                'total_cpu_usage_percent': total_cpu,
                'strategy_type_distribution': strategy_types,
                'uptime': time.time() if self.running else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    def _health_check_loop(self):
        """Health check loop for all containers"""
        while self.running:
            try:
                for strategy_name, container in list(self.containers.items()):
                    if not container.health_check():
                        logger.warning(f"Health check failed for strategy: {strategy_name}")
                        
                        if self.config.auto_restart_failed:
                            logger.info(f"Auto-restarting failed strategy: {strategy_name}")
                            container.restart()
                
                time.sleep(self.config.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(self.config.health_check_interval)
    
    def cleanup(self):
        """Clean up all containers and resources"""
        try:
            for container in self.containers.values():
                container.cleanup()
            self.containers.clear()
            logger.info("Cleaned up all containers")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup() 