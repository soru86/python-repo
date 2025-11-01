import pandas as pd
from app import flask_app
from shared.config.config import get_config
from binance.client import Client
from binance.client import Client
from datetime import datetime
from flask import current_app

# Get config from current app context or use default
def get_binance_api_key():
    try:
        return current_app.config.get('BINANCE_API_KEY') or flask_app.config.get('BINANCE_API_KEY')
    except:
        return None

def get_binance_api_secret():
    try:
        return current_app.config.get('BINANCE_API_SECRET') or flask_app.config.get('BINANCE_API_SECRET')
    except:
        return None

BINANCE_API_KEY = get_binance_api_key()
BINANCE_API_SECRET = get_binance_api_secret()

# Initialize Binance client
def get_binance_client():
    """Get Binance client instance"""
    try:
        return Client(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)
    except Exception as e:
        print(f"Error initializing Binance client: {e}")
        return None

def fetch_binance_data(symbol, interval, start_str, end_str, data_type='spot'):
    """Fetch historical data from Binance"""
    try:
        client = get_binance_client()
        if not client:
            return None
            
        if data_type == 'futures':
            klines = client.futures_historical_klines(symbol, interval, start_str, end_str)
        else:
            klines = client.get_historical_klines(symbol, interval, start_str, end_str)
            
        data = pd.DataFrame(
            klines,
            columns=[
                "Open time", "Open", "High", "Low", "Close", "Volume",
                "Close time", "Quote asset volume", "Number of trades",
                "Taker buy base asset volume", "Taker buy quote asset volume", "Ignore"
            ]
        )
        data["Open time"] = pd.to_datetime(data["Open time"], unit="ms")
        data["Close"] = data["Close"].astype(float)
        data["High"] = data["High"].astype(float)
        data["Low"] = data["Low"].astype(float)
        data["Open"] = data["Open"].astype(float)
        data["Volume"] = data["Volume"].astype(float)
        data.set_index("Open time", inplace=True)
        return data
    except Exception as e:
        print(f"Error fetching Binance data: {e}")
        return None

def get_binance_realtime_data(symbol):
    """Get real-time data from Binance"""
    try:
        client = get_binance_client()
        if not client:
            return None
            
        # Get 24hr ticker
        ticker = client.get_ticker(symbol=symbol)
        
        # Get current price
        price = client.get_symbol_ticker(symbol=symbol)
        
        data = {
            "symbol": symbol,
            "price": float(price['price']),
            "change": float(ticker['priceChange']),
            "changePercent": float(ticker['priceChangePercent']),
            "volume": float(ticker['volume']),
            "high": float(ticker['highPrice']),
            "low": float(ticker['lowPrice']),
            "open": float(ticker['openPrice']),
            "timestamp": int(datetime.now().timestamp())
        }
        
        return data
    except Exception as e:
        print(f"Error fetching Binance real-time data: {e}")
        return None

def place_binance_order(order_data):
    """Place order on Binance"""
    try:
        client = get_binance_client()
        if not client:
            return {"success": False, "error": "Binance client not available"}
            
        # Extract order parameters
        symbol = order_data.get('symbol')
        side = order_data.get('side', 'BUY')
        order_type = order_data.get('orderType', 'MARKET')
        quantity = order_data.get('quantity')
        price = order_data.get('price')
        
        if order_type == 'MARKET':
            if side == 'BUY':
                order = client.order_market_buy(symbol=symbol, quantity=quantity)
            else:
                order = client.order_market_sell(symbol=symbol, quantity=quantity)
        elif order_type == 'LIMIT':
            if side == 'BUY':
                order = client.order_limit_buy(symbol=symbol, quantity=quantity, price=str(price))
            else:
                order = client.order_limit_sell(symbol=symbol, quantity=quantity, price=str(price))
        else:
            return {"success": False, "error": "Unsupported order type"}
            
        return {"success": True, "data": order}
    except Exception as e:
        print(f"Error placing Binance order: {e}")
        return {"success": False, "error": str(e)}

def get_binance_account_info():
    """Get Binance account information"""
    try:
        client = get_binance_client()
        if not client:
            return None
            
        account = client.get_account()
        return account
    except Exception as e:
        print(f"Error fetching Binance account info: {e}")
        return None

def get_binance_open_orders(symbol=None):
    """Get open orders from Binance"""
    try:
        client = get_binance_client()
        if not client:
            return None
            
        if symbol:
            orders = client.get_open_orders(symbol=symbol)
        else:
            orders = client.get_open_orders()
            
        return orders
    except Exception as e:
        print(f"Error fetching Binance open orders: {e}")
        return None

def cancel_binance_order(symbol, order_id):
    """Cancel order on Binance"""
    try:
        client = get_binance_client()
        if not client:
            return {"success": False, "error": "Binance client not available"}
            
        result = client.cancel_order(symbol=symbol, orderId=order_id)
        return {"success": True, "data": result}
    except Exception as e:
        print(f"Error canceling Binance order: {e}")
        return {"success": False, "error": str(e)}

# Utility functions for external use
def is_binance_available():
    """Check if Binance API is available"""
    try:
        client = get_binance_client()
        if not client:
            return False
        client.get_server_time()
        return True
    except:
        return False

def get_supported_symbols():
    """Get list of supported symbols on Binance"""
    try:
        client = get_binance_client()
        if not client:
            return []
            
        exchange_info = client.get_exchange_info()
        symbols = [symbol['symbol'] for symbol in exchange_info['symbols'] if symbol['status'] == 'TRADING']
        return symbols
    except Exception as e:
        print(f"Error getting supported symbols: {e}")
        return [] 