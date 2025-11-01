import requests
import json
from shared.constants.constants import intervals
from . import indian_market_bp
from flask import jsonify, request, current_app
from datetime import datetime, timedelta
from app import flask_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Unified Indian market data endpoint that routes to authenticated brokers
from blueprints.indian_market.fyers.routes import is_fyers_authenticated
from blueprints.indian_market.dhan.routes import is_dhan_authenticated

# Import utilities
from shared.utils.websocket_utils import socketio

# Get config from current app context or use default
def get_base_url():
    try:
        return current_app.config.get('BASE_URL') or flask_app.config.get('BASE_URL') or 'http://localhost:8000'
    except:
        return 'http://localhost:8000'

BASE_URL = get_base_url()

# Setup Rate Limiting
def get_limiter():
    try:
        return Limiter(
            app=current_app or flask_app,
            key_func=get_remote_address,
            default_limits=[(current_app or flask_app).config.get('RATE_LIMIT_DEFAULT', '100 per minute')],
            storage_uri=(current_app or flask_app).config.get('RATE_LIMIT_STORAGE_URL', 'redis://localhost:6379/1')
        )
    except:
        return None

limiter = get_limiter()

@indian_market_bp.route('/realtime')
def get_indian_realtime_data():
    symbol = request.args.get('symbol', 'RELIANCE')

    # Try Fyers first
    if is_fyers_authenticated():
        try:
            response = requests.get(f"{BASE_URL}/fyers/market-data/realtime?symbol={symbol}")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Fyers real-time data fetch failed: {e}")

    # Try Dhan if Fyers fails
    if is_dhan_authenticated():
        try:
            response = requests.get(f"{BASE_URL}/dhan/market-data/realtime?symbol={symbol}")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Dhan real-time data fetch failed: {e}")

    # Return error if no authenticated brokers
    return jsonify({
        "success": False,
        "error": "No authenticated brokers available. Please connect to Fyers or Dhan first."
    }), 400

@indian_market_bp.route('/order', methods=['POST'])
def place_indian_order():
    """Place order for Indian stocks through authenticated brokers"""
    order_data = request.json
    
    # Try Fyers first
    if is_fyers_authenticated():
        try:
            response = requests.post(f"{BASE_URL}/fyers/market-data/order", json=order_data)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Fyers order placement failed: {e}")
    
    # Try Dhan if Fyers fails
    if is_dhan_authenticated():
        try:
            response = requests.post(f"{BASE_URL}/dhan/market-data/order", json=order_data)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Dhan order placement failed: {e}")
    
    # Return error if no authenticated brokers
    return jsonify({
        "success": False,
        "error": "No authenticated brokers available. Please connect to Fyers or Dhan first."
    }), 400

# Additional unified endpoints for account management
@indian_market_bp.route('/account')
def get_indian_account_info():
    """Get account information from authenticated brokers"""
    
    # Try Fyers first
    if is_fyers_authenticated():
        try:
            response = requests.get(f"{BASE_URL}/fyers/market-data/account")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Fyers account info fetch failed: {e}")
    
    # Try Dhan if Fyers fails
    if is_dhan_authenticated():
        try:
            response = requests.get(f"{BASE_URL}/dhan/market-data/account")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Dhan account info fetch failed: {e}")
    
    return jsonify({"error": "No authenticated brokers available"}), 401

@indian_market_bp.route('/positions')
def get_indian_positions():
    """Get positions from authenticated brokers"""
    
    # Try Fyers first
    if is_fyers_authenticated():
        try:
            response = requests.get(f"{BASE_URL}/fyers/market-data/positions")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Fyers positions fetch failed: {e}")
    
    # Try Dhan if Fyers fails
    if is_dhan_authenticated():
        try:
            response = requests.get(f"{BASE_URL}/dhan/market-data/positions")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Dhan positions fetch failed: {e}")
    
    return jsonify({"error": "No authenticated brokers available"}), 401

@indian_market_bp.route('/orders')
def get_indian_orders():
    """Get open orders from authenticated brokers"""
    
    # Try Fyers first
    if is_fyers_authenticated():
        try:
            response = requests.get(f"{BASE_URL}/fyers/market-data/orders")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Fyers orders fetch failed: {e}")
    
    # Try Dhan if Fyers fails
    if is_dhan_authenticated():
        try:
            response = requests.get(f"{BASE_URL}/dhan/market-data/orders")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Dhan orders fetch failed: {e}")
    
    return jsonify({"error": "No authenticated brokers available"}), 401

# Unified Indian market data endpoints
@indian_market_bp.route('/')
@indian_market_bp.route('')  # Handle requests without trailing slash
@limiter.limit("100 per minute")
def get_indian_market_data():
    """Get Indian market data from authenticated brokers"""
    try:
        symbol = request.args.get('symbol', 'RELIANCE')
        interval = request.args.get('interval', '1h')
        
        flask_app.logger.info("Fetching Indian market data", symbol=symbol, interval=interval)
        
        # Try Fyers first
        if is_fyers_authenticated():
            try:
                response = requests.get(f"{BASE_URL}/fyers/market-data/historical?symbol={symbol}&interval={interval}")
                if response.status_code == 200:
                    return response.json()
            except Exception as e:
                flask_app.logger.warning("Fyers data fetch failed", error=str(e))
        
        # Try Dhan if Fyers fails
        if is_dhan_authenticated():
            try:
                # Dhan only supports daily and above intervals
                # For minute and hourly data, we need to use a different approach
                if interval in intervals:
                    # For intraday data, use the new intraday API endpoint
                    flask_app.logger.info(f"Using Dhan intraday API for {interval} interval")
                    print(f"📊 Using Dhan intraday API for {interval} interval")
                    
                    response = requests.get(f"{BASE_URL}/indian-market/dhan/market-data/intraday?symbol={symbol}&interval={interval}")
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Convert Dhan intraday data to chart format
                        if isinstance(data, dict):
                            chart_data = []
                            
                            # Handle array format from Dhan API
                            if 'close' in data and isinstance(data['close'], list):
                                # Data is in array format: {close: [...], high: [...], low: [...], open: [...], timestamp: [...]}
                                timestamps = data.get('timestamp', [])
                                opens = data.get('open', [])
                                highs = data.get('high', [])
                                lows = data.get('low', [])
                                closes = data.get('close', [])
                                volumes = data.get('volume', [])
                                
                                for i in range(len(timestamps)):
                                    if i < len(opens) and i < len(highs) and i < len(lows) and i < len(closes):
                                        chart_data.append({
                                            'time': int(timestamps[i]) + 19800,  # Add 5 hours 30 minutes (19800 seconds) for IST
                                            'open': float(opens[i]),
                                            'high': float(highs[i]),
                                            'low': float(lows[i]),
                                            'close': float(closes[i]),
                                            'volume': float(volumes[i]) if i < len(volumes) else 0
                                        })
                            
                            # Handle object array format (fallback)
                            elif 'data' in data and isinstance(data['data'], list):
                                for item in data['data']:
                                    chart_data.append({
                                        'time': int(datetime.strptime(item.get('date', ''), '%Y-%m-%d').timestamp()) + 19800,  # Add 5 hours 30 minutes (19800 seconds) for IST
                                        'open': float(item.get('open', 0)),
                                        'high': float(item.get('high', 0)),
                                        'low': float(item.get('low', 0)),
                                        'close': float(item.get('close', 0)),
                                        'volume': float(item.get('volume', 0))
                                    })
                            
                            socketio.emit('new_record', chart_data)
                            socketio.sleep(1)
                            return chart_data
                        else:
                            socketio.emit('new_record', data)
                            socketio.sleep(1)
                            return data
                
                # Convert interval to date range for Dhan API
                end_date = datetime.now()
                if interval in ['1d', '1D']:
                    start_date = end_date - timedelta(days=30)  # 1 month for daily data
                elif interval in ['3d', '3D']:
                    start_date = end_date - timedelta(days=90)  # 3 months for 3-day data
                elif interval in ['1w', '1W']:
                    start_date = end_date - timedelta(days=180)  # 6 months for weekly data
                elif interval in ['1M', '3M', '1Y']:
                    start_date = end_date - timedelta(days=365)  # 1 year for monthly/yearly data
                else:
                    start_date = end_date - timedelta(days=30)  # Default to 1 month
                
                from_date = start_date.strftime('%Y-%m-%d')
                to_date = end_date.strftime('%Y-%m-%d')
                
                response = requests.get(f"{BASE_URL}/indian-market/dhan/market-data/historical?symbol={symbol}&from_date={from_date}&to_date={to_date}")
                if response.status_code == 200:
                    data = response.json()
                    
                    # Convert Dhan historical data to chart format
                    if isinstance(data, dict):
                        chart_data = []
                        
                        # Handle array format from Dhan API
                        if 'close' in data and isinstance(data['close'], list):
                            # Data is in array format: {close: [...], high: [...], low: [...], open: [...], timestamp: [...]}
                            timestamps = data.get('timestamp', [])
                            opens = data.get('open', [])
                            highs = data.get('high', [])
                            lows = data.get('low', [])
                            closes = data.get('close', [])
                            volumes = data.get('volume', [])
                            
                            for i in range(len(timestamps)):
                                if i < len(opens) and i < len(highs) and i < len(lows) and i < len(closes):
                                    chart_data.append({
                                        'time': int(timestamps[i]) + 19800,  # Add 5 hours 30 minutes (19800 seconds) for IST
                                        'open': float(opens[i]),
                                        'high': float(highs[i]),
                                        'low': float(lows[i]),
                                        'close': float(closes[i]),
                                        'volume': float(volumes[i]) if i < len(volumes) else 0
                                    })
                        
                        # Handle object array format (fallback)
                        elif 'data' in data and isinstance(data['data'], list):
                            for item in data['data']:
                                chart_data.append({
                                    'time': int(datetime.strptime(item.get('date', ''), '%Y-%m-%d').timestamp()) + 19800,  # Add 5 hours 30 minutes (19800 seconds) for IST
                                    'open': float(item.get('open', 0)),
                                    'high': float(item.get('high', 0)),
                                    'low': float(item.get('low', 0)),
                                    'close': float(item.get('close', 0)),
                                    'volume': float(item.get('volume', 0))
                                })
                        
                            socketio.emit('new_record', chart_data)
                            socketio.sleep(1)
                            return chart_data
                        else:
                            socketio.emit('new_record', data)
                            socketio.sleep(1)
                            return data
            except Exception as e:
                flask_app.logger.warning("Dhan data fetch failed", error=str(e))
        
        # Return error if no authenticated brokers
        return jsonify({
            "success": False,
            "error": "No authenticated brokers available. Please connect to Fyers or Dhan first.",
            "message": "To get market data, please authenticate with a broker first.",
            "available_brokers": ["Fyers", "Dhan"],
            "endpoints": {
                "fyers_login": "/indian-market/fyers/login",
                "dhan_login": "/indian-market/dhan/login"
            }
        }), 401
        
    except Exception as e:
        flask_app.logger.error("Error fetching Indian market data", error=str(e))
        return jsonify({
            "success": False,
            "error": f"Failed to fetch market data: {str(e)}"
        }), 500

@indian_market_bp.route('/test-real-time-chart', methods=['GET'])
def test_real_time_chart_data():
    """
    Read the JSON file once, then emit one record per second.
    For very large files, consider streaming or chunk-reading.
    """
    with open('mockdata/chart_mock_data.json') as f:
        records = json.load(f)

    # sorted_records = sorted(records, key=lambda x: int(x["time"]))
    print("sorted_records: ", records)
    for record in records:
        # print("current record: ", record)
        socketio.emit('new_record', record)
        # flush so connected clients immediately receive it
        socketio.sleep(1)  # non-blocking sleep under eventlet