"""
Redis Streams Manager for Algorithmic Trading

This module handles real-time market data distribution using Redis Streams.
Each trading strategy container reads from its own consumer group to ensure
reliable message delivery and fault tolerance.
"""

import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import redis
from shared.utils.redis_db import redis_db

logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """Market data structure for Redis Streams"""
    symbol: str
    price: float
    volume: float
    timestamp: int
    exchange: str
    data_type: str  # 'tick', 'ohlc', 'trade'
    additional_data: Dict[str, Any] = None

class RedisStreamsManager:
    """Manages Redis Streams for real-time market data distribution"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client or redis_db.redis_client
        self.stream_prefix = "market_data"
        self.consumer_groups = {}
        
    def create_stream_key(self, exchange: str, symbol: str, data_type: str = "tick") -> str:
        """Create standardized stream key"""
        return f"{self.stream_prefix}:{exchange}:{symbol}:{data_type}"
    
    def publish_market_data(self, market_data: MarketData) -> bool:
        """
        Publish market data to Redis Stream
        
        Args:
            market_data: MarketData object containing tick/OHLC data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            stream_key = self.create_stream_key(
                market_data.exchange, 
                market_data.symbol, 
                market_data.data_type
            )
            
            # Prepare data for Redis Stream
            stream_data = {
                'symbol': market_data.symbol,
                'price': str(market_data.price),
                'volume': str(market_data.volume),
                'timestamp': str(market_data.timestamp),
                'exchange': market_data.exchange,
                'data_type': market_data.data_type,
                'additional_data': json.dumps(market_data.additional_data or {})
            }
            
            # Add to stream with auto-generated ID
            message_id = self.redis_client.xadd(stream_key, stream_data)
            
            logger.info(f"Published market data to {stream_key}: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing market data: {e}")
            return False
    
    def create_consumer_group(self, stream_key: str, group_name: str) -> bool:
        """
        Create a consumer group for a stream
        
        Args:
            stream_key: Redis stream key
            group_name: Name of the consumer group
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if stream exists, create if not
            stream_info = self.redis_client.xinfo_stream(stream_key)
            if not stream_info:
                # Create empty stream first
                self.redis_client.xadd(stream_key, {'init': 'true'})
                # Remove the init message
                self.redis_client.xtrim(stream_key, maxlen=0)
            
            # Create consumer group
            self.redis_client.xgroup_create(stream_key, group_name, id='0', mkstream=True)
            logger.info(f"Created consumer group {group_name} for stream {stream_key}")
            return True
            
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"Consumer group {group_name} already exists for {stream_key}")
                return True
            else:
                logger.error(f"Error creating consumer group: {e}")
                return False
        except Exception as e:
            logger.error(f"Error creating consumer group: {e}")
            return False
    
    def read_market_data(self, stream_key: str, group_name: str, consumer_name: str, 
                        count: int = 10, block_ms: int = 5000) -> List[Tuple[str, Dict]]:
        """
        Read market data from Redis Stream using consumer group
        
        Args:
            stream_key: Redis stream key
            group_name: Consumer group name
            consumer_name: Consumer name within the group
            count: Maximum number of messages to read
            block_ms: Block time in milliseconds
            
        Returns:
            List of tuples (message_id, data_dict)
        """
        try:
            # Ensure consumer group exists
            self.create_consumer_group(stream_key, group_name)
            
            # Read messages from stream
            messages = self.redis_client.xreadgroup(
                group_name, consumer_name, {stream_key: '>'}, 
                count=count, block=block_ms
            )
            
            if not messages:
                return []
            
            # Process messages
            result = []
            for stream, stream_messages in messages:
                for message_id, data in stream_messages:
                    # Parse additional_data
                    if 'additional_data' in data:
                        try:
                            data['additional_data'] = json.loads(data['additional_data'])
                        except:
                            data['additional_data'] = {}
                    
                    # Convert string values back to appropriate types
                    if 'price' in data:
                        data['price'] = float(data['price'])
                    if 'volume' in data:
                        data['volume'] = float(data['volume'])
                    if 'timestamp' in data:
                        data['timestamp'] = int(data['timestamp'])
                    
                    result.append((message_id, data))
            
            return result
            
        except Exception as e:
            logger.error(f"Error reading market data: {e}")
            return []
    
    def acknowledge_message(self, stream_key: str, group_name: str, message_id: str) -> bool:
        """
        Acknowledge a message to remove it from pending list
        
        Args:
            stream_key: Redis stream key
            group_name: Consumer group name
            message_id: Message ID to acknowledge
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.redis_client.xack(stream_key, group_name, message_id)
            return True
        except Exception as e:
            logger.error(f"Error acknowledging message: {e}")
            return False
    
    def get_pending_messages(self, stream_key: str, group_name: str, 
                           consumer_name: str = None) -> List[Dict]:
        """
        Get pending messages for a consumer group
        
        Args:
            stream_key: Redis stream key
            group_name: Consumer group name
            consumer_name: Optional consumer name filter
            
        Returns:
            List of pending message dictionaries
        """
        try:
            pending = self.redis_client.xpending(stream_key, group_name)
            return pending
        except Exception as e:
            logger.error(f"Error getting pending messages: {e}")
            return []
    
    def claim_pending_messages(self, stream_key: str, group_name: str, 
                             consumer_name: str, min_idle_time: int = 60000) -> List[Tuple[str, Dict]]:
        """
        Claim pending messages that have been idle for too long
        
        Args:
            stream_key: Redis stream key
            group_name: Consumer group name
            consumer_name: Consumer name to claim messages for
            min_idle_time: Minimum idle time in milliseconds
            
        Returns:
            List of claimed message tuples (message_id, data)
        """
        try:
            claimed = self.redis_client.xclaim(
                stream_key, group_name, consumer_name, min_idle_time
            )
            return claimed
        except Exception as e:
            logger.error(f"Error claiming pending messages: {e}")
            return []
    
    def get_stream_info(self, stream_key: str) -> Dict[str, Any]:
        """
        Get information about a Redis stream
        
        Args:
            stream_key: Redis stream key
            
        Returns:
            Dictionary containing stream information
        """
        try:
            info = self.redis_client.xinfo_stream(stream_key)
            return info
        except Exception as e:
            logger.error(f"Error getting stream info: {e}")
            return {}
    
    def trim_stream(self, stream_key: str, max_len: int = 1000) -> int:
        """
        Trim stream to keep only the latest messages
        
        Args:
            stream_key: Redis stream key
            max_len: Maximum number of messages to keep
            
        Returns:
            Number of messages removed
        """
        try:
            removed = self.redis_client.xtrim(stream_key, maxlen=max_len)
            return removed
        except Exception as e:
            logger.error(f"Error trimming stream: {e}")
            return 0

# Global Redis Streams manager instance
streams_manager = RedisStreamsManager() 