"""
Docker Utilities for Algorithmic Trading

This module provides utilities for:
- Building strategy container images
- Managing Docker networks and volumes
- Container health monitoring
- Resource allocation and optimization
"""

import os
import json
import logging
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path
import docker
from docker.errors import DockerException, BuildError

logger = logging.getLogger(__name__)

class DockerUtils:
    """
    Docker utilities for algorithmic trading container management
    
    This class provides:
    - Image building and management
    - Network configuration
    - Volume management
    - Resource monitoring
    """
    
    def __init__(self, docker_client=None):
        self.docker_client = docker_client or docker.from_env()
        self.base_image = 'python:3.9-slim'
        self.strategy_image = 'trading-strategy'
        
    def build_strategy_image(self, dockerfile_path: str = None) -> bool:
        """
        Build the strategy container image
        
        Args:
            dockerfile_path: Path to Dockerfile (optional)
            
        Returns:
            bool: True if build successful, False otherwise
        """
        try:
            if not dockerfile_path:
                dockerfile_path = self._create_dockerfile()
            
            # Build the image
            logger.info(f"Building strategy image from {dockerfile_path}")
            
            build_result = self.docker_client.images.build(
                path=os.path.dirname(dockerfile_path),
                dockerfile=os.path.basename(dockerfile_path),
                tag=self.strategy_image,
                rm=True,
                pull=True
            )
            
            logger.info(f"Successfully built strategy image: {self.strategy_image}")
            return True
            
        except BuildError as e:
            logger.error(f"Failed to build strategy image: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error building strategy image: {e}")
            return False
    
    def _create_dockerfile(self) -> str:
        """Create a Dockerfile for strategy containers"""
        dockerfile_content = """
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy strategy code
COPY algo/ ./algo/
COPY shared/ ./shared/

# Create non-root user
RUN useradd -m -u 1000 trader && chown -R trader:trader /app
USER trader

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import redis; redis.Redis(host='redis', port=6379).ping()" || exit 1

# Default command
CMD ["python", "-m", "algo.strategy_runner"]
"""
        
        # Create requirements.txt for strategy containers
        requirements_content = """
redis>=4.0.0
numpy>=1.21.0
pandas>=1.3.0
docker>=5.0.0
flask>=2.0.0
requests>=2.25.0
websocket-client>=1.0.0
python-dotenv>=0.19.0
"""
        
        # Write files
        dockerfile_path = "/tmp/Dockerfile.strategy"
        requirements_path = "/tmp/requirements.strategy.txt"
        
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        with open(requirements_path, 'w') as f:
            f.write(requirements_content)
        
        return dockerfile_path
    
    def create_network(self, network_name: str = 'trading-network') -> bool:
        """
        Create Docker network for strategy containers
        
        Args:
            network_name: Name of the network to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if network already exists
            existing_networks = self.docker_client.networks.list(names=[network_name])
            if existing_networks:
                logger.info(f"Network {network_name} already exists")
                return True
            
            # Create network
            self.docker_client.networks.create(
                network_name,
                driver='bridge',
                labels={'trading': 'strategy-network'}
            )
            
            logger.info(f"Created network: {network_name}")
            return True
            
        except DockerException as e:
            logger.error(f"Failed to create network {network_name}: {e}")
            return False
    
    def create_volume(self, volume_name: str = 'strategy-data') -> bool:
        """
        Create Docker volume for strategy data persistence
        
        Args:
            volume_name: Name of the volume to create
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if volume already exists
            existing_volumes = self.docker_client.volumes.list(filters={'name': volume_name})
            if existing_volumes:
                logger.info(f"Volume {volume_name} already exists")
                return True
            
            # Create volume
            self.docker_client.volumes.create(
                volume_name,
                labels={'trading': 'strategy-data'}
            )
            
            logger.info(f"Created volume: {volume_name}")
            return True
            
        except DockerException as e:
            logger.error(f"Failed to create volume {volume_name}: {e}")
            return False
    
    def get_container_stats(self, container_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed statistics for a container
        
        Args:
            container_name: Name of the container
            
        Returns:
            Dict containing container statistics or None if not found
        """
        try:
            container = self.docker_client.containers.get(container_name)
            stats = container.stats(stream=False)
            
            if not stats:
                return None
            
            # Parse memory statistics
            memory_stats = stats.get('memory_stats', {})
            memory_usage = memory_stats.get('usage', 0) / (1024 * 1024)  # MB
            memory_limit = memory_stats.get('limit', 0) / (1024 * 1024)  # MB
            
            # Parse CPU statistics
            cpu_stats = stats.get('cpu_stats', {})
            cpu_usage = 0
            if 'cpu_usage' in cpu_stats and 'total_usage' in cpu_stats['cpu_usage']:
                cpu_delta = cpu_stats['cpu_usage']['total_usage']
                system_delta = cpu_stats.get('system_cpu_usage', 0)
                if system_delta > 0:
                    cpu_usage = (cpu_delta / system_delta) * 100
            
            # Parse network statistics
            network_stats = stats.get('networks', {})
            network_io = {}
            for interface, data in network_stats.items():
                network_io[interface] = {
                    'rx_bytes': data.get('rx_bytes', 0),
                    'tx_bytes': data.get('tx_bytes', 0)
                }
            
            return {
                'container_name': container_name,
                'memory_usage_mb': memory_usage,
                'memory_limit_mb': memory_limit,
                'memory_percent': (memory_usage / memory_limit * 100) if memory_limit > 0 else 0,
                'cpu_usage_percent': cpu_usage,
                'network_io': network_io,
                'timestamp': stats.get('read', 0)
            }
            
        except DockerException as e:
            logger.error(f"Error getting stats for container {container_name}: {e}")
            return None
    
    def cleanup_unused_resources(self) -> Dict[str, int]:
        """
        Clean up unused Docker resources
        
        Returns:
            Dict containing cleanup statistics
        """
        try:
            stats = {
                'containers_removed': 0,
                'images_removed': 0,
                'networks_removed': 0,
                'volumes_removed': 0
            }
            
            # Remove stopped containers
            stopped_containers = self.docker_client.containers.list(
                filters={'status': 'exited'}
            )
            for container in stopped_containers:
                container.remove()
                stats['containers_removed'] += 1
            
            # Remove unused images
            unused_images = self.docker_client.images.list(
                filters={'dangling': True}
            )
            for image in unused_images:
                self.docker_client.images.remove(image.id)
                stats['images_removed'] += 1
            
            # Remove unused networks
            networks = self.docker_client.networks.list()
            for network in networks:
                if not network.attrs['Containers']:
                    network.remove()
                    stats['networks_removed'] += 1
            
            # Remove unused volumes
            volumes = self.docker_client.volumes.list()
            for volume in volumes:
                if not volume.attrs['Status']['Mountpoint']:
                    volume.remove()
                    stats['volumes_removed'] += 1
            
            logger.info(f"Cleanup completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {}
    
    def get_system_resources(self) -> Dict[str, Any]:
        """
        Get system resource usage for Docker
        
        Returns:
            Dict containing system resource information
        """
        try:
            info = self.docker_client.info()
            
            return {
                'containers': info['Containers'],
                'images': info['Images'],
                'driver': info['Driver'],
                'kernel_version': info['KernelVersion'],
                'os_type': info['OSType'],
                'architecture': info['Architecture'],
                'docker_version': info['ServerVersion'],
                'memory_limit': info.get('MemoryLimit', False),
                'swap_limit': info.get('SwapLimit', False),
                'kernel_memory': info.get('KernelMemory', False),
                'cpu_cfs_period': info.get('CPUCfsPeriod', False),
                'cpu_cfs_quota': info.get('CPUCfsQuota', False),
                'cpu_shares': info.get('CPUShares', False),
                'cpu_set': info.get('CPUSet', False),
                'ipv4_forwarding': info.get('IPv4Forwarding', False),
                'bridge_nf_iptables': info.get('BridgeNfIptables', False),
                'bridge_nf_ip6tables': info.get('BridgeNfIp6tables', False),
                'debug': info.get('Debug', False),
                'nfd': info.get('NFd', 0),
                'n_goroutines': info.get('NGoroutines', 0),
                'system_time': info.get('SystemTime', ''),
                'logging_driver': info.get('LoggingDriver', ''),
                'cgroup_driver': info.get('CgroupDriver', ''),
                'kernel_version': info.get('KernelVersion', ''),
                'operating_system': info.get('OperatingSystem', ''),
                'os_version': info.get('OSVersion', ''),
                'hostname': info.get('Name', ''),
                'n_cpus': info.get('NCPU', 0),
                'memory': info.get('MemTotal', 0),
                'index_server_address': info.get('IndexServerAddress', ''),
                'registry_config': info.get('RegistryConfig', {}),
                'n_events_listener': info.get('NEventsListener', 0),
                'n_goroutines': info.get('NGoroutines', 0),
                'init_binary': info.get('InitBinary', ''),
                'containerd_commit': info.get('ContainerdCommit', {}),
                'runc_commit': info.get('RuncCommit', {}),
                'init_commit': info.get('InitCommit', {}),
                'security_options': info.get('SecurityOptions', []),
                'product_license': info.get('ProductLicense', ''),
                'warnings': info.get('Warnings', [])
            }
            
        except Exception as e:
            logger.error(f"Error getting system resources: {e}")
            return {} 