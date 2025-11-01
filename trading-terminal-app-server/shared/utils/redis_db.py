import json
import time
from typing import Optional, Dict, Any
from shared.config.config import get_config

# Try to import redis, fallback to mock if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: Redis not available, using in-memory storage")

class MockRedis:
    """Mock Redis implementation for when Redis is not available"""
    
    def __init__(self):
        self.data = {}
    
    def set(self, key, value):
        self.data[key] = value
        return True
    
    def get(self, key):
        return self.data.get(key)
    
    def delete(self, key):
        if key in self.data:
            del self.data[key]
        return True
    
    def keys(self, pattern):
        import re
        pattern = pattern.replace('*', '.*')
        return [key for key in self.data.keys() if re.match(pattern, key)]
    
    def ping(self):
        return True

class RedisDB:
    """Redis database utility for connecting Redis server"""
    
    def __init__(self):
        if REDIS_AVAILABLE:
            try:
                config = get_config('development')
                self.redis_client = redis.Redis(
                    host=config.REDIS_HOST,
                    port=config.REDIS_PORT,
                    db=config.REDIS_DB,
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                print("✅ Connected to Redis successfully")
            except Exception as e:
                print(f"Warning: Redis connection failed, using in-memory storage: {e}")
                self.redis_client = MockRedis()
        else:
            self.redis_client = MockRedis()
        
    def set_current_user_auth_data(self, user_id: str, user_auth_data: Dict[str, Any]) -> bool | None:
        """Redis database utility for storing user auth session data for current user"""
        try:
            key = f"current_user_auth_data:{user_id}"
            
            # Store data as JSON string
            self.redis_client.set(key, json.dumps(user_auth_data))
            return True
        except Exception as e:
            print(f"Error setting user auth session data in Redis: {e}")
            return False

    def get_current_user_auth_data(self, user_id: str) -> Any:
        """Redis database utility for getting user auth session data for current user"""
        try:
            key = f"current_user_auth_data:{user_id}"
            data = self.redis_client.get(key)
            
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Error getting user auth session data from Redis: {e}")
            return None

    def delete_current_user_auth_data(self, user_id: str) -> bool | None:
        """Redis database utility for deleting user auth session data for current user"""
        try:
            key = f"current_user_auth_data:{user_id}"
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Error deleting user auth session data from Redis: {e}")
            return False

    def set_user_data(self, user_id: str, symbol: str, data: Dict[str, Any]) -> bool:
        """
        Store user data in Redis with key format: user_data:{user_id}:{symbol}
        
        Args:
            user_id: User identifier
            symbol: Trading symbol (e.g., BTCUSDT, RELIANCE)
            data: Dictionary containing the data to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = f"user_data:{user_id}:{symbol}"
            
            # Add timestamp if not present
            if 'timestamp' not in data:
                data['timestamp'] = int(time.time())
            
            # Store data as JSON string
            self.redis_client.set(key, json.dumps(data))
            return True
        except Exception as e:
            print(f"Error setting user data in Redis: {e}")
            return False
    
    def get_user_data(self, user_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user data from Redis
        
        Args:
            user_id: User identifier
            symbol: Trading symbol
            
        Returns:
            Dict containing the data or None if not found
        """
        try:
            key = f"user_data:{user_id}:{symbol}"
            data = self.redis_client.get(key)
            
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Error getting user data from Redis: {e}")
            return None
    
    def set_access_token(self, user_id: str, broker: str, token_data: Dict[str, Any]) -> bool:
        """
        Store access token for a user and broker
        
        Args:
            user_id: User identifier
            broker: Broker name (e.g., 'dhan', 'fyers')
            token_data: Dictionary containing token and related data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = f"access_token:{user_id}:{broker}"
            
            # Add timestamp if not present
            if 'timestamp' not in token_data:
                token_data['timestamp'] = int(time.time())
            
            # Store token data as JSON string
            self.redis_client.set(key, json.dumps(token_data))
            return True
        except Exception as e:
            print(f"Error setting access token in Redis: {e}")
            return False
    
    def get_access_token(self, user_id: str, broker: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve access token for a user and broker
        
        Args:
            user_id: User identifier
            broker: Broker name
            
        Returns:
            Dict containing token data or None if not found
        """
        try:
            key = f"access_token:{user_id}:{broker}"
            data = self.redis_client.get(key)
            
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Error getting access token from Redis: {e}")
            return None
    
    def delete_access_token(self, user_id: str, broker: str) -> bool:
        """
        Delete access token for a user and broker
        
        Args:
            user_id: User identifier
            broker: Broker name
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = f"access_token:{user_id}:{broker}"
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Error deleting access token from Redis: {e}")
            return False
    
    def set_user_profile(self, user_id: str, broker: str, profile_data: Dict[str, Any]) -> bool:
        """
        Store user profile data
        
        Args:
            user_id: User identifier
            broker: Broker name
            profile_data: Dictionary containing profile information
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = f"user_profile:{user_id}:{broker}"
            
            # Add timestamp if not present
            if 'timestamp' not in profile_data:
                profile_data['timestamp'] = int(time.time())
            
            # Store profile data as JSON string
            self.redis_client.set(key, json.dumps(profile_data))
            return True
        except Exception as e:
            print(f"Error setting user profile in Redis: {e}")
            return False
    
    def get_user_profile(self, user_id: str, broker: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user profile data
        
        Args:
            user_id: User identifier
            broker: Broker name
            
        Returns:
            Dict containing profile data or None if not found
        """
        try:
            key = f"user_profile:{user_id}:{broker}"
            data = self.redis_client.get(key)
            
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Error getting user profile from Redis: {e}")
            return None
    
    def set_market_data(self, symbol: str, data: Dict[str, Any]) -> bool:
        """
        Store market data for a symbol
        
        Args:
            symbol: Trading symbol
            data: Dictionary containing market data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = f"market_data:{symbol}"
            
            # Add timestamp if not present
            if 'timestamp' not in data:
                data['timestamp'] = int(time.time())
            
            # Store market data as JSON string
            self.redis_client.set(key, json.dumps(data))
            return True
        except Exception as e:
            print(f"Error setting market data in Redis: {e}")
            return False
    
    def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve market data for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dict containing market data or None if not found
        """
        try:
            key = f"market_data:{symbol}"
            data = self.redis_client.get(key)
            
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Error getting market data from Redis: {e}")
            return None
    
    def get_all_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Get all data for a specific user
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict containing all user data
        """
        try:
            pattern = f"user_data:{user_id}:*"
            keys = self.redis_client.keys(pattern)
            
            user_data = {}
            for key in keys:
                data = self.redis_client.get(key)
                if data:
                    symbol = key.split(':')[-1]
                    user_data[symbol] = json.loads(data)
            
            return user_data
        except Exception as e:
            print(f"Error getting all user data from Redis: {e}")
            return {}
    
    def delete_user_data(self, user_id: str, symbol: str) -> bool:
        """
        Delete specific user data
        
        Args:
            user_id: User identifier
            symbol: Trading symbol
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = f"user_data:{user_id}:{symbol}"
            self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Error deleting user data from Redis: {e}")
            return False
    
    def clear_user_data(self, user_id: str) -> bool:
        """
        Clear all data for a specific user
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            pattern = f"*:{user_id}:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                self.redis_client.delete(*keys)
            return True
        except Exception as e:
            print(f"Error clearing user data from Redis: {e}")
            return False
    
    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            print(f"Redis health check failed: {e}")
            return False

# Global Redis instance
redis_db = RedisDB() 