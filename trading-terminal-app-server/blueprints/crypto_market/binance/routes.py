from . import binance_bp
from flask import jsonify, request
from datetime import datetime
from blueprints.crypto_market.binance.binance_utils import fetch_binance_data, get_binance_realtime_data, place_binance_order, get_binance_account_info, get_binance_open_orders, cancel_binance_order, get_binance_client

@binance_bp.route('/data', methods=['GET'])
def get_binance_data():
    """Get historical data from Binance"""
    symbol = request.args.get('symbol', 'RELIANCE')
    interval = request.args.get('interval', '1h')
    start = request.args.get('start', '1 day ago UTC')
    end = request.args.get('end', None)
    data_type = request.args.get('type', 'spot')
    
    try:
        df = fetch_binance_data(symbol, interval, start, end, data_type)
        if df is None:
            return jsonify({"error": "Failed to fetch data from Binance"}), 400
            
        result = [
            {
                "time": int(idx.timestamp()),
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"],
                "volume": row["Volume"]
            }
            for idx, row in df.iterrows()
        ]
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_binance_data: {e}")
        return jsonify({"error": str(e)}), 400

@binance_bp.route('/realtime', methods=['GET'])
def get_binance_realtime():
    """Get real-time data from Binance"""
    symbol = request.args.get('symbol', 'RELIANCE')
    
    try:
        data = get_binance_realtime_data(symbol)
        if data is None:
            return jsonify({"error": "Failed to fetch real-time data from Binance"}), 400
            
        return jsonify(data)
    except Exception as e:
        print(f"Error in get_binance_realtime: {e}")
        return jsonify({"error": str(e)}), 400

@binance_bp.route('/order', methods=['POST'])
def place_binance_order_route():
    """Place order on Binance"""
    try:
        order_data = request.json
        if not order_data:
            return jsonify({"error": "No order data provided"}), 400
            
        result = place_binance_order(order_data)
        return jsonify(result)
    except Exception as e:
        print(f"Error in place_binance_order_route: {e}")
        return jsonify({"error": str(e)}), 400

@binance_bp.route('/account', methods=['GET'])
def get_binance_account():
    """Get Binance account information"""
    try:
        account = get_binance_account_info()
        if account is None:
            return jsonify({"error": "Failed to fetch account information"}), 400
            
        return jsonify(account)
    except Exception as e:
        print(f"Error in get_binance_account: {e}")
        return jsonify({"error": str(e)}), 400

@binance_bp.route('/orders', methods=['GET'])
def get_binance_orders():
    """Get open orders from Binance"""
    symbol = request.args.get('symbol', None)
    
    try:
        orders = get_binance_open_orders(symbol)
        if orders is None:
            return jsonify({"error": "Failed to fetch open orders"}), 400
            
        return jsonify(orders)
    except Exception as e:
        print(f"Error in get_binance_orders: {e}")
        return jsonify({"error": str(e)}), 400

@binance_bp.route('/order/cancel', methods=['POST'])
def cancel_binance_order_route():
    """Cancel order on Binance"""
    try:
        data = request.json
        symbol = data.get('symbol')
        order_id = data.get('orderId')
        
        if not symbol or not order_id:
            return jsonify({"error": "Symbol and orderId are required"}), 400
            
        result = cancel_binance_order(symbol, order_id)
        return jsonify(result)
    except Exception as e:
        print(f"Error in cancel_binance_order_route: {e}")
        return jsonify({"error": str(e)}), 400

@binance_bp.route('/status', methods=['GET'])
def get_binance_status():
    """Check Binance API status"""
    try:
        client = get_binance_client()
        if not client:
            return jsonify({"status": "disconnected", "error": "Client not available"})
            
        # Test API connection
        server_time = client.get_server_time()
        return jsonify({
            "status": "connected",
            "server_time": server_time,
            "timestamp": int(datetime.now().timestamp())
        })
    except Exception as e:
        print(f"Error in get_binance_status: {e}")
        return jsonify({"status": "error", "error": str(e)}), 400