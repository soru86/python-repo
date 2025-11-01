"""
Strategy Container for Docker-based Algorithmic Trading

This module provides the container wrapper for running trading strategies
in isolated Docker containers with Redis Streams integration.
"""

import json
import time
import logging
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import docker
from docker.errors import DockerException, ImageNotFound

logger = logging.getLogger(__name__)

@dataclass
class ContainerConfig:
    """Container configuration structure"""
    strategy_name: str
    strategy_type: str  # 'moving_average', 'rsi', 'macd', 'bollinger_bands'
    symbols: List[str]
    exchange: str
    parameters: Dict[str, Any]
    risk_management: Dict[str, Any]
    redis_host: str = 'redis'
    redis_port: int = 6379
    container_name: str = None
    image_name: str = 'trading-strategy'
    memory_limit: str = '512m'
    cpu_limit: str = '0.5'

class StrategyContainer:
    """
    Docker container wrapper for trading strategy execution
    
    This class manages:
    - Container lifecycle (start, stop, restart)
    - Strategy configuration injection
    - Redis Streams connectivity
    - Performance monitoring
    - Log collection
    """
    
    def __init__(self, config: ContainerConfig):
        self.config = config
        self.container_name = config.container_name or f"strategy_{config.strategy_name}_{int(time.time())}"
        self.docker_client = None
        self.container = None
        self.status = 'stopped'
        self.start_time = None
        self.logs = []
        self.simulation_mode = False
        
        # Try to initialize Docker client, but don't fail if not available
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized successfully for strategy container")
            
            # Check if the required image exists
            try:
                self.docker_client.images.get(self.config.image_name)
                logger.info(f"Docker image {self.config.image_name} found")
            except ImageNotFound:
                logger.warning(f"Docker image {self.config.image_name} not found. Running in simulation mode.")
                self.simulation_mode = True
                
        except Exception as e:
            logger.warning(f"Docker not available for strategy container: {e}. Running in simulation mode.")
            self.docker_client = None
            self.simulation_mode = True
        
        logger.info(f"Initialized strategy container: {self.container_name}")
    
    def start(self) -> bool:
        """Start the strategy container"""
        try:
            if self.docker_client is None or self.simulation_mode:
                # Docker not available or image not found, run in simulation mode
                logger.info(f"Running strategy {self.config.strategy_name} in simulation mode")
                self.status = 'running'
                self.start_time = datetime.now()
                self.logs.append(f"[{datetime.now()}] Strategy {self.config.strategy_name} started in simulation mode")
                return True
            
            # Prepare environment variables
            env_vars = {
                'STRATEGY_NAME': self.config.strategy_name,
                'STRATEGY_TYPE': self.config.strategy_type,
                'SYMBOLS': json.dumps(self.config.symbols),
                'EXCHANGE': self.config.exchange,
                'PARAMETERS': json.dumps(self.config.parameters),
                'RISK_MANAGEMENT': json.dumps(self.config.risk_management),
                'REDIS_HOST': self.config.redis_host,
                'REDIS_PORT': str(self.config.redis_port),
                'CONTAINER_NAME': self.container_name
            }
            
            # Create and start container
            self.container = self.docker_client.containers.run(
                image=self.config.image_name,
                name=self.container_name,
                environment=env_vars,
                detach=True,
                restart_policy={'Name': 'unless-stopped'},
                mem_limit=self.config.memory_limit,
                cpu_quota=int(float(self.config.cpu_limit) * 100000),
                cpu_period=100000,
                network_mode='host',  # Use host networking for Redis access
                volumes={
                    '/var/run/docker.sock': {'bind': '/var/run/docker.sock', 'mode': 'ro'}
                }
            )
            
            self.status = 'running'
            self.start_time = datetime.now()
            
            logger.info(f"Started strategy container: {self.container_name}")
            return True
            
        except DockerException as e:
            logger.error(f"Failed to start container {self.container_name}: {e}")
            # Fall back to simulation mode
            logger.info(f"Falling back to simulation mode for strategy {self.config.strategy_name}")
            self.simulation_mode = True
            self.status = 'running'
            self.start_time = datetime.now()
            self.logs.append(f"[{datetime.now()}] Strategy {self.config.strategy_name} started in simulation mode (Docker failed: {e})")
            return True
        except Exception as e:
            logger.error(f"Unexpected error starting container {self.container_name}: {e}")
            # Fall back to simulation mode
            logger.info(f"Falling back to simulation mode for strategy {self.config.strategy_name}")
            self.simulation_mode = True
            self.status = 'running'
            self.start_time = datetime.now()
            self.logs.append(f"[{datetime.now()}] Strategy {self.config.strategy_name} started in simulation mode (Error: {e})")
            return True
    
    def stop(self) -> bool:
        """Stop the strategy container"""
        try:
            if self.docker_client is None or self.simulation_mode:
                # Docker not available, just update status
                logger.info(f"Stopping strategy {self.config.strategy_name} in simulation mode")
                self.status = 'stopped'
                self.logs.append(f"[{datetime.now()}] Strategy {self.config.strategy_name} stopped in simulation mode")
                return True
            
            if self.container:
                self.container.stop(timeout=30)
                self.container.remove()
                self.container = None
                self.status = 'stopped'
                logger.info(f"Stopped strategy container: {self.container_name}")
                return True
            return False
        except DockerException as e:
            logger.error(f"Failed to stop container {self.container_name}: {e}")
            # Update status anyway
            self.status = 'stopped'
            return True
    
    def restart(self) -> bool:
        """Restart the strategy container"""
        try:
            if self.stop():
                time.sleep(2)  # Wait for container to fully stop
                return self.start()
            return False
        except Exception as e:
            logger.error(f"Failed to restart container {self.container_name}: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get container status and statistics"""
        try:
            if self.simulation_mode:
                # Return simulation status
                uptime = None
                if self.start_time:
                    uptime = (datetime.now() - self.start_time).total_seconds()
                
                return {
                    'name': self.container_name,
                    'status': self.status,
                    'running': self.status == 'running',
                    'uptime': uptime,
                    'memory_usage': None,  # Not available in simulation mode
                    'cpu_usage': None,     # Not available in simulation mode
                    'strategy_name': self.config.strategy_name,
                    'strategy_type': self.config.strategy_type,
                    'symbols': self.config.symbols,
                    'simulation_mode': True
                }
            
            if not self.container:
                return {
                    'name': self.container_name,
                    'status': 'stopped',
                    'running': False,
                    'strategy_name': self.config.strategy_name,
                    'strategy_type': self.config.strategy_type,
                    'symbols': self.config.symbols
                }
            
            # Get container stats
            stats = None
            try:
                stats = self.container.stats(stream=False)
            except Exception as e:
                logger.warning(f"Could not get container stats: {e}")
            
            # Calculate uptime
            uptime = None
            if self.start_time:
                uptime = (datetime.now() - self.start_time).total_seconds()
            
            # Parse memory and CPU usage
            memory_usage = None
            cpu_usage = None
            
            if stats:
                # Memory usage (in MB)
                memory_stats = stats.get('memory_stats', {})
                if 'usage' in memory_stats:
                    memory_usage = memory_stats['usage'] / (1024 * 1024)
                
                # CPU usage percentage
                cpu_stats = stats.get('cpu_stats', {})
                if 'cpu_usage' in cpu_stats and 'total_usage' in cpu_stats['cpu_usage']:
                    cpu_delta = cpu_stats['cpu_usage']['total_usage']
                    system_delta = cpu_stats.get('system_cpu_usage', 0)
                    if system_delta > 0:
                        cpu_usage = (cpu_delta / system_delta) * 100
            
            return {
                'name': self.container_name,
                'status': self.container.status,
                'running': self.container.status == 'running',
                'uptime': uptime,
                'memory_usage': memory_usage,
                'cpu_usage': cpu_usage,
                'strategy_name': self.config.strategy_name,
                'strategy_type': self.config.strategy_type,
                'symbols': self.config.symbols,
                'simulation_mode': False
            }
            
        except Exception as e:
            logger.error(f"Error getting container status: {e}")
            return {
                'name': self.container_name,
                'status': 'error',
                'running': False,
                'error': str(e),
                'simulation_mode': self.simulation_mode
            }
    
    def get_logs(self, tail: int = 100) -> List[str]:
        """Get container logs"""
        try:
            if self.simulation_mode:
                # Return simulation logs
                return self.logs[-tail:] if self.logs else []
            
            if not self.container:
                return []
            
            logs = self.container.logs(tail=tail, timestamps=True).decode('utf-8')
            return logs.split('\n') if logs else []
            
        except Exception as e:
            logger.error(f"Error getting container logs: {e}")
            return []
    
    def update_config(self, new_config: ContainerConfig) -> bool:
        """Update container configuration and restart if needed"""
        try:
            # Check if configuration has changed
            if (self.config.parameters != new_config.parameters or 
                self.config.risk_management != new_config.risk_management):
                
                self.config = new_config
                
                # Restart container with new configuration
                if self.status == 'running':
                    logger.info(f"Updating configuration for container: {self.container_name}")
                    return self.restart()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating container configuration: {e}")
            return False
    
    def health_check(self) -> bool:
        """Perform health check on the container"""
        try:
            if self.simulation_mode:
                # In simulation mode, just check if status is running
                return self.status == 'running'
            
            if not self.container:
                return False
            
            # Check if container is running
            self.container.reload()
            if self.container.status != 'running':
                return False
            
            # Check if container is responding (optional ping test)
            # This could be extended to check strategy-specific health endpoints
            
            return True
            
        except Exception as e:
            logger.error(f"Health check failed for container {self.container_name}: {e}")
            return False
    
    def cleanup(self):
        """Clean up container resources"""
        try:
            if self.container:
                self.container.remove(force=True)
                self.container = None
            self.status = 'stopped'
            logger.info(f"Cleaned up container: {self.container_name}")
        except Exception as e:
            logger.error(f"Error cleaning up container {self.container_name}: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup() 