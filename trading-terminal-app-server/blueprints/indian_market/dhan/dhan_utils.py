import requests
import json
import time
import threading
import logging
import asyncio
import websockets
import struct
import datetime
from typing import Dict, Any, Optional
from . import dhan_session
from shared.utils.redis_db import redis_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Additional Dhan-specific functions can be added here
def get_dhan_session():
    """Get current Dhan session data"""
    return dhan_session

def clear_dhan_session():
    """Clear Dhan session data"""
    global dhan_session
    dhan_session = {}

def is_dhan_authenticated(user_id='default_user'):
    """Check if Dhan is authenticated using Redis"""
    token_data = redis_db.get_access_token(user_id, 'dhan')
    return token_data is not None and token_data.get('access_token')

def get_dhan_access_token(user_id='default_user'):
    """Get Dhan access token from Redis"""
    token_data = redis_db.get_access_token(user_id, 'dhan')
    return token_data.get('access_token') if token_data else None

def validate_jwt_token(jwt_token):
    """Validate JWT token by making a request to Dhan profile API"""
    try:
        headers = {
            'access-token': jwt_token
        }
        
        # Make GET request to Dhan profile API
        url = "https://api.dhan.co/v2/profile"
        response = requests.get(url, headers=headers)
        
        return response.status_code == 200
    except Exception as e:
        print(f"JWT token validation failed: {e}")
        return False

def get_user_profile_with_jwt(jwt_token):
    """Get user profile using JWT token"""
    try:
        headers = {
            'access-token': jwt_token
        }
        
        # Make GET request to Dhan profile API
        url = "https://api.dhan.co/v2/profile"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        print(f"Failed to get user profile with JWT: {e}")
        return None

class RealtimeService:
    """WebSocket service for real-time market data from Dhan using working implementation"""
    
    def __init__(self):
        self.ws = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        self.thread = None
        self.stop_event = threading.Event()
        self.subscribed_symbols = set()
        self.loop = None
        
    def get_dhan_credentials(self, user_id: str = 'default_user') -> Optional[Dict[str, str]]:
        """
        Get Dhan access token and client ID from Redis
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict containing access_token and client_id, or None if not found
        """
        try:
            # Get access token
            token_data = redis_db.get_access_token(user_id, 'dhan')
            if not token_data:
                logger.warning(f"No access token found for user {user_id}")
                return None
                
            # Get user profile for client ID
            profile_data = redis_db.get_user_profile(user_id, 'dhan')
            if not profile_data:
                logger.warning(f"No profile data found for user {user_id}")
                return None
                
            access_token = token_data.get('access_token')
            client_id = profile_data.get('dhanClientId') or profile_data.get('client_id')
            
            if not access_token or not client_id:
                logger.warning(f"Missing access_token or client_id for user {user_id}")
                return None
                
            return {
                'access_token': access_token,
                'client_id': client_id
            }
        except Exception as e:
            logger.error(f"Error getting Dhan credentials: {e}")
            return None
    
    def build_websocket_url(self, access_token: str, client_id: str) -> str:
        """
        Build WebSocket URL for Dhan realtime API
        
        Args:
            access_token: Dhan access token
            client_id: Dhan client ID
            
        Returns:
            WebSocket URL string
        """
        return f"wss://api-feed.dhan.co?version=2&token={access_token}&clientId={client_id}&authType=2"
    
    def decode_packet(self, msg_bytes):
        """Decode binary packet from Dhan WebSocket"""
        if len(msg_bytes) < 16:
            return None

        msg_type = msg_bytes[0]
        security_id = struct.unpack('<I', msg_bytes[4:8])[0]

        if msg_type == 2:  # Ticker
            ltp = struct.unpack('<f', msg_bytes[8:12])[0]
            ts_raw = struct.unpack('<I', msg_bytes[12:16])[0]
            
            if not (0 < ltp < 1e6):
                return None
                
            # Convert to IST (UTC + 5:30)
            if ts_raw > 2147483647:
                ts_raw = ts_raw // 1000
            
            utc_time = datetime.datetime.fromtimestamp(ts_raw)
            ist_time = utc_time + datetime.timedelta(hours=6, minutes=30)
            
            return {
                "Type": "Ticker",
                "SecurityId": security_id,
                "LTP": round(ltp, 2),
                "Time": ist_time.strftime("%H:%M:%S"),
                "symbol": self.get_symbol_from_security_id(security_id)
            }

        elif msg_type == 6:  # Prev Close
            prev_close = struct.unpack('<f', msg_bytes[8:12])[0]
            prev_oi = struct.unpack('<I', msg_bytes[12:16])[0]
            
            if not (0 < prev_close < 1e6):
                return None
                
            return {
                "Type": "PrevClose",
                "SecurityId": security_id,
                "PrevClose": round(prev_close, 2),
                "PrevOI": prev_oi,
                "symbol": self.get_symbol_from_security_id(security_id)
            }
        
        return None
    
    def get_symbol_from_security_id(self, security_id: int) -> str:
        """Map security ID to symbol"""
        security_map = {
            1333: "RELIANCE",
            11536: "TCS", 
            341: "HDFCBANK",
            450135: "CRUDEOILM-19Aug2025-FUT"
        }
        return security_map.get(security_id, "UNKNOWN")
    
    def get_instrument_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get instrument data for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'RELIANCE')
            
        Returns:
            Instrument data with RequestCode and InstrumentList
        """
        # Map common symbols to their instrument data
        instrument_map = {
            'RELIANCE': {
                "RequestCode": 15,
                "InstrumentCount": 2,
                "InstrumentList": [
                    {
                        "ExchangeSegment": "NSE_EQ",
                        "SecurityId": "1333"
                    },
                    {
                        "ExchangeSegment": "BSE_EQ",
                        "SecurityId": "532540"
                    }
                ]
            },
            'TCS': {
                "RequestCode": 15,
                "InstrumentCount": 2,
                "InstrumentList": [
                    {
                        "ExchangeSegment": "NSE_EQ",
                        "SecurityId": "11536"
                    },
                    {
                        "ExchangeSegment": "BSE_EQ",
                        "SecurityId": "532540"
                    }
                ]
            },
            'HDFCBANK': {
                "RequestCode": 15,
                "InstrumentCount": 2,
                "InstrumentList": [
                    {
                        "ExchangeSegment": "NSE_EQ",
                        "SecurityId": "341"
                    },
                    {
                        "ExchangeSegment": "BSE_EQ",
                        "SecurityId": "500180"
                    }
                ]
            },
            'CRUDEOILM-19Aug2025-FUT': {
                "RequestCode": 15,
                "InstrumentCount": 1,
                "InstrumentList": [
                    {
                        "ExchangeSegment": "MCX_COMM",
                        "SecurityId": "450135"
                    }
                ]
            }
        }
        
        # Get the instrument data
        instrument_data = instrument_map.get(symbol.upper(), {
            "RequestCode": 15,
            "InstrumentCount": 1,
            "InstrumentList": [
                {
                    "ExchangeSegment": "NSE_EQ",
                    "SecurityId": "1333"  # Default to RELIANCE
                }
            ]
        })
        
        # Add instrument type based on symbol
        if 'FUT' in symbol.upper():
            instrument_data['instrument_type'] = 'FUTURES'
        elif 'OPT' in symbol.upper():
            instrument_data['instrument_type'] = 'OPTIONS'
        else:
            instrument_data['instrument_type'] = 'EQUITY'
        
        return instrument_data
    
    async def handle_message(self, message):
        """Handle incoming WebSocket messages"""
        try:
            if isinstance(message, bytes):
                data = self.decode_packet(message)
                if data:
                    symbol = data.get('symbol', 'UNKNOWN')
                    logger.info(f"Received realtime data: {data}")
                    
                    # Store in Redis
                    market_data = {
                        'symbol': symbol,
                        'timestamp': int(time.time()),
                        'data': data,
                        'price': data.get('LTP', 0),
                        'volume': data.get('volume', 0),
                        'change': data.get('change', 0),
                        'change_percent': data.get('change_percent', 0),
                        'high': data.get('high', 0),
                        'low': data.get('low', 0),
                        'open': data.get('open', 0),
                        'last_update': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    redis_db.set_market_data(f"realtime:{symbol}", market_data)
                    redis_db.redis_client.set(f"realtime:{symbol}:latest", json.dumps(market_data))
                    
                    logger.info(f"Realtime data stored for {symbol}")
            else:
                logger.info(f"Received text message: {message}")
                
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    async def websocket_handler(self, ws_url: str, subscription_payload: dict):
        """Handle WebSocket connection using asyncio"""
        try:
            async with websockets.connect(ws_url) as ws:
                await ws.send(json.dumps(subscription_payload))
                logger.info("✅ Connected to Dhan WebSocket")
                self.is_connected = True
                self.reconnect_attempts = 0

                while not self.stop_event.is_set():
                    try:
                        message = await ws.recv()
                        await self.handle_message(message)
                    except websockets.exceptions.ConnectionClosed:
                        logger.error("❌ Connection closed")
                        break
                    except Exception as e:
                        logger.error(f"❌ Error: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            self.is_connected = False
    
    def schedule_reconnect(self):
        """Schedule a reconnection attempt"""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            logger.info(f"Scheduling reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts} in {self.reconnect_delay} seconds")
            
            def reconnect():
                time.sleep(self.reconnect_delay)
                if not self.stop_event.is_set():
                    self.start()
            
            threading.Thread(target=reconnect, daemon=True).start()
        else:
            logger.error("Max reconnection attempts reached")
    
    def start(self, user_id: str = 'default_user'):
        """
        Start the WebSocket connection using asyncio
        
        Args:
            user_id: User identifier for getting credentials
        """
        try:
            logger.info(f"Starting realtime service for user: {user_id}")
            
            # Get credentials
            credentials = self.get_dhan_credentials(user_id)
            if not credentials:
                logger.error("Failed to get Dhan credentials")
                return
            
            access_token = credentials['access_token']
            client_id = credentials['client_id']
            
            logger.info(f"Retrieved credentials - Client ID: {client_id}")
            
            # Build WebSocket URL
            ws_url = self.build_websocket_url(access_token, client_id)
            logger.info(f"Connecting to WebSocket: {ws_url}")
            
            # Create subscription payload for subscribed symbols
            subscription_payload = {
                "RequestCode": 15,
                "InstrumentCount": 3,
                "InstrumentList": [
                    {
                        "ExchangeSegment": "NSE_EQ",
                        "SecurityId": "1333"  # RELIANCE
                    },
                    {
                        "ExchangeSegment": "MCX_COMM",
                        "SecurityId": "450135"  # CRUDEOILM-19Aug2025-FUT
                    },
                    {
                        "ExchangeSegment": "NSE_EQ",
                        "SecurityId": "11536"  # TCS
                    }
                ]
            }
            
            # Start async WebSocket in a separate thread
            def run_async_websocket():
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                try:
                    self.loop.run_until_complete(self.websocket_handler(ws_url, subscription_payload))
                except Exception as e:
                    logger.error(f"Async WebSocket error: {e}")
                finally:
                    self.loop.close()
            
            self.thread = threading.Thread(target=run_async_websocket, daemon=True)
            self.thread.start()
            
            logger.info("Async WebSocket thread started")
            
        except Exception as e:
            logger.error(f"Error starting WebSocket connection: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def stop(self):
        """Stop the WebSocket connection"""
        logger.info("Stopping WebSocket connection")
        self.stop_event.set()
        
        if self.loop and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
    
    def get_realtime_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get realtime data for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Realtime data or None if not found
        """
        try:
            # Try to get from Redis
            realtime_data = redis_db.get_market_data(f"realtime:{symbol}")
            if realtime_data:
                return realtime_data
            
            # Fallback to latest key
            latest_data = redis_db.redis_client.get(f"realtime:{symbol}:latest")
            if latest_data:
                return json.loads(latest_data)
            
            return None
        except Exception as e:
            logger.error(f"Error getting realtime data for {symbol}: {e}")
            return None
    
    def subscribe_to_symbol(self, symbol: str):
        """Subscribe to a symbol for realtime updates"""
        self.subscribed_symbols.add(symbol)
        logger.info(f"Added {symbol} to subscription list")
    
    def is_running(self) -> bool:
        """Check if the WebSocket service is running"""
        return self.is_connected and not self.stop_event.is_set()

# Global realtime service instance
realtime_service = RealtimeService()