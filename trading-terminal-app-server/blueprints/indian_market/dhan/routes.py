import os
import time
import logging
import requests
import urllib.parse
from . import dhan_bp
from app import flask_app
from . import dhan_session
from shared.utils.redis_db import redis_db
from flask import jsonify, request, redirect, session, current_app
from blueprints.indian_market.dhan.dhan_utils import is_dhan_authenticated, get_dhan_access_token
from shared.utils.common_utils import isDebugLogging
from shared.utils.timeframe_utils import (
    EXCHANGE_MAP, TIMEFRAME_MAP,
    get_dhan_exchange_segment, get_dhan_timeframe, validate_trading_params,
    get_timeframe_based_dates, map_interval_to_timeframe,
    get_timeframe_ranges_info, get_exchange_options, get_timeframe_options,
    get_interval_options
)

# Configure logging for this module
logger = logging.getLogger(__name__)

# Get config from current app context or use default
def get_dhan_api_base():
    try:
        return current_app.config.get('DHAN_API_BASE') or flask_app.config.get('DHAN_API_BASE')
    except:
        return None

DHAN_API_BASE = get_dhan_api_base()

@dhan_bp.route('/test')
def dhan_test():
    """Test endpoint to verify Dhan integration is working"""
    return jsonify({
        "status": "success",
        "message": "Dhan integration is working",
        "endpoints": {
            "health": "/indian-market/dhan/health",
            "profile": "/indian-market/dhan/profile (requires access-token header)",
            "status": "/indian-market/dhan/status",
            "login": "/indian-market/dhan/login"
        },
        "timestamp": time.time()
    })

@dhan_bp.route('/health')
def dhan_health():
    """Health check endpoint for Dhan integration"""
    return jsonify({
        "status": "healthy",
        "service": "dhan",
        "timestamp": time.time(),
        "message": "Dhan integration is running"
    })

@dhan_bp.route('/profile')
def dhan_profile():
    """Get user profile using JWT token and store in Redis"""
    jwt_token = request.headers.get('access-token')
    user_id = request.headers.get('user-id', 'default_user')  # Default user ID if not provided
    
    # If no JWT token provided, check if user is already authenticated via Redis
    if not jwt_token:
        # Check if user has existing profile in Redis
        existing_profile = redis_db.get_user_profile(user_id, 'dhan')
        if existing_profile:
            return jsonify({
                "message": "Using cached profile data",
                "profile": existing_profile,
                "cached": True
            })
        
        return jsonify({
            "error": "Missing access-token header",
            "message": "Please provide a valid JWT token in the 'access-token' header",
            "required_headers": ["access-token", "user-id (optional)"],
            "example": {
                "headers": {
                    "access-token": "your_jwt_token_here",
                    "user-id": "default_user"
                }
            }
        }), 400
    
    try:
        # Set headers
        headers = {
            'access-token': jwt_token
        }

        # Make GET request to Dhan profile API
        url = "https://api.dhan.co/v2/profile"
        response = requests.get(url, headers=headers)

        if isDebugLogging():
            logger.debug(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            profile_data = response.json()
            
            if isDebugLogging():
                logger.debug(f"Response JSON: {profile_data}")
            
            # Add welcome message and client ID to profile data
            # Use dhanClientId from the API response
            client_id = profile_data.get('dhanClientId', profile_data.get('client_id', 'N/A'))
            token_validity = profile_data.get('tokenValidity', 'N/A')
            active_segments = profile_data.get('activeSegment', 'N/A')
            
            enhanced_profile = {
                **profile_data,
                'welcome_message': f"Welcome to Dhan Trading! Client ID: {client_id}",
                'client_id': client_id,
                'token_validity': token_validity,
                'active_segments': active_segments,
                'connection_status': 'Connected',
                'broker': 'dhan'
            }
            
            # Store access token and profile data in Redis
            token_data = {
                'access_token': jwt_token,
                'broker': 'dhan',
                'user_id': user_id,
                'profile': enhanced_profile
            }
            
            # Save to Redis
            redis_db.set_access_token(user_id, 'dhan', token_data)
            redis_db.set_user_profile(user_id, 'dhan', enhanced_profile)
            
            if isDebugLogging():
                logger.debug(f"Stored Dhan access token for user {user_id} in Redis")
                logger.debug(f"Welcome message: {enhanced_profile['welcome_message']}")
            
            return jsonify(enhanced_profile)
        else:
            error_message = f"Dhan API error: {response.status_code}"
            try:
                error_data = response.json()
                error_message = error_data.get('message', error_data.get('error', error_message))
            except:
                pass
            
            return jsonify({
                "error": error_message,
                "status_code": response.status_code,
                "message": "Failed to fetch profile from Dhan API"
            }), response.status_code
            
    except Exception as e:
        logger.error(f"Dhan profile fetch failed: {e}")
        return jsonify({
            "error": f"Failed to fetch profile: {str(e)}",
            "message": "An error occurred while connecting to Dhan API"
        }), 500

@dhan_bp.route('/login')
def dhan_login():
    """Initiate Dhan OAuth flow (kept for backward compatibility)"""
    client_id = request.args.get('client_id')
    secret_key = request.args.get('secret_key')
    redirect_uri = request.args.get('redirect_uri', 'http://localhost:8000/dhan/callback')
    
    if not client_id or not secret_key:
        return jsonify({"error": "Missing client_id or secret_key"}), 400
    
    # Store credentials in session
    session['dhan_client_id'] = client_id
    session['dhan_secret_key'] = secret_key
    session['dhan_redirect_uri'] = redirect_uri

    if isDebugLogging():
        logger.debug(f"Session set in /dhan/login: {session.get('dhan_client_id')}, {session.get('dhan_secret_key')}, {session.get('dhan_redirect_uri')}")

    # Redirect to Dhan authorization page
    dhan_auth_url = (
        f"{DHAN_API_BASE}/oauth/authorize?"
        f"client_id={client_id}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri, safe='')}&"
        f"response_type=code&"
        f"scope=read,write&"
        f"state=None"
    )
    
    return redirect(dhan_auth_url)

@dhan_bp.route('/callback')
def dhan_callback():
    """Handle Dhan OAuth callback (kept for backward compatibility)"""
    if isDebugLogging():
        logger.debug("---- /dhan/callback called ----")
    
    auth_code = request.args.get('code')

    if not auth_code:
        return jsonify({"error": "No authorization code received"}), 400

    # Get stored credentials from session
    client_id = session.get('dhan_client_id')
    secret_key = session.get('dhan_secret_key')
    redirect_uri = session.get('dhan_redirect_uri', 'http://localhost:8000/dhan/callback')

    if not client_id or not secret_key:
        return jsonify({"error": "Missing stored credentials"}), 400

    if isDebugLogging():
        logger.debug(f"Session in /dhan/callback: {client_id}, {secret_key}, {redirect_uri}")

    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": secret_key,
        "code": auth_code,
        "redirect_uri": redirect_uri
    }

    try:
        if isDebugLogging():
            logger.debug(f"Making token request to: {DHAN_API_BASE}/oauth/token")
            logger.debug(f"Payload: {payload}")
        
        response = requests.post(f"{DHAN_API_BASE}/oauth/token", json=payload)
        
        if isDebugLogging():
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {response.headers}")
        
        data = response.json()
        
        if isDebugLogging():
            logger.debug(f"Response data: {data}")

        if data.get("access_token"):
            # Store in global session (in production, use proper session management)
            dhan_session['access_token'] = data["access_token"]
            dhan_session['client_id'] = client_id
            dhan_session['code'] = auth_code
            
            # Get user profile
            access_token = data["access_token"]

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            if isDebugLogging():
                logger.debug(f"Making profile request to: {DHAN_API_BASE}/user/profile")
            
            profile_response = requests.get(f"{DHAN_API_BASE}/user/profile", headers=headers)
            profile_data = profile_response.json()
            
            if isDebugLogging():
                logger.debug(f"Profile response: {profile_data}")
            
            dhan_session['profile'] = profile_data.get('data', {})
            
            # Get the actual client ID from profile data
            actual_client_id = profile_data.get('data', {}).get('dhanClientId', client_id)
            
            # Return HTML page that closes the popup and communicates with parent
            success_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Dhan Authentication Success</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        text-align: center;
                        padding: 50px;
                        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                        color: white;
                    }}
                    .success-message {{
                        background: rgba(16, 185, 129, 0.1);
                        border: 1px solid #10b981;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    .welcome-message {{
                        background: rgba(59, 130, 246, 0.1);
                        border: 1px solid #3b82f6;
                        border-radius: 8px;
                        padding: 16px;
                        margin: 16px 0;
                        font-weight: 500;
                    }}
                    .client-id {{
                        background: rgba(255, 255, 255, 0.1);
                        border: 1px solid #64748b;
                        border-radius: 6px;
                        padding: 8px 12px;
                        margin: 8px 0;
                        font-family: monospace;
                        font-size: 12px;
                        color: #94a3b8;
                    }}
                    .spinner {{
                        border: 2px solid #f3f3f3;
                        border-top: 2px solid #10b981;
                        border-radius: 50%;
                        width: 20px;
                        height: 20px;
                        animation: spin 1s linear infinite;
                        margin: 10px auto;
                    }}
                    @keyframes spin {{
                        0% {{ transform: rotate(0deg); }}
                        100% {{ transform: rotate(360deg); }}
                    }}
                </style>
            </head>
            <body>
                <div class="success-message">
                    <h2>✅ Authentication Successful!</h2>
                    <p>Successfully connected to Dhan</p>
                    <div class="welcome-message">
                        <h3>🎉 Welcome to Dhan Trading!</h3>
                        <p>Your account has been successfully connected.</p>
                        <div class="client-id">
                            Client ID: {actual_client_id}
                        </div>
                    </div>
                    <div class="spinner"></div>
                    <p>Closing window...</p>
                </div>
                <script>
                    // Send message to parent window
                    if (window.opener) {{
                        window.opener.postMessage({{
                            type: 'dhan_auth_success',
                            data: {{
                                success: true,
                                message: 'Successfully authenticated with Dhan',
                                access_token: '{data["access_token"]}',
                                profile: {profile_data.get('data', {})}
                            }}
                        }}, '*');
                    }}
                    
                    // Close the popup after a short delay
                    setTimeout(() => {{
                        window.close();
                    }}, 2000);
                </script>
            </body>
            </html>
            """
            
            return success_html
        else:
            # Return error HTML page
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Dhan Authentication Failed</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        text-align: center;
                        padding: 50px;
                        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                        color: white;
                    }}
                    .error-message {{
                        background: rgba(239, 68, 68, 0.1);
                        border: 1px solid #ef4444;
                        border-radius: 8px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="error-message">
                    <h2>❌ Authentication Failed</h2>
                    <p>Token request failed: {data}</p>
                    <button onclick="window.close()" style="
                        background: #ef4444;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 5px;
                        cursor: pointer;
                    ">Close Window</button>
                </div>
                <script>
                    // Send error message to parent window
                    if (window.opener) {{
                        window.opener.postMessage({{
                            type: 'dhan_auth_error',
                            data: {{
                                success: false,
                                error: 'Token request failed: {data}'
                            }}
                        }}, '*');
                    }}
                </script>
            </body>
            </html>
            """
            
            return error_html
            
    except Exception as e:
        return jsonify({"error": f"Authentication failed: {str(e)}"}), 500

@dhan_bp.route('/status')
def dhan_status():
    """Check Dhan authentication status from Redis"""
    user_id = request.args.get('user_id', 'default_user')
    
    # Check Redis for access token
    token_data = redis_db.get_access_token(user_id, 'dhan')
    profile_data = redis_db.get_user_profile(user_id, 'dhan')

    if not token_data:
        return jsonify({
            "isLoggedIn": False,
            "message": "Not authenticated"
        })
    
    # Add welcome message if profile data exists
    welcome_info = {}
    if profile_data:
        # Use dhanClientId from the API response
        client_id = profile_data.get('dhanClientId', profile_data.get('client_id', 'N/A'))
        token_validity = profile_data.get('tokenValidity', 'N/A')
        active_segments = profile_data.get('activeSegment', 'N/A')
        welcome_info = {
            "welcome_message": f"Welcome to Dhan Trading! Client ID: {client_id}",
            "client_id": client_id,
            "token_validity": token_validity,
            "active_segments": active_segments,
            "connection_status": "Connected"
        }
    
    return jsonify({
        "isLoggedIn": True,
        "profile": profile_data or {},
        "user_id": user_id,
        "broker": "dhan",
        **welcome_info
    })

@dhan_bp.route('/logout')
def dhan_logout():
    """Logout from Dhan and clear Redis data"""
    user_id = request.args.get('user_id', 'default_user')
    
    # Clear Redis data
    redis_db.delete_access_token(user_id, 'dhan')
    
    # Also clear session for backward compatibility
    global dhan_session
    dhan_session = {}
    session.clear()
    
    return jsonify({"success": True, "message": "Logged out successfully"})

@dhan_bp.route('/api-status')
def dhan_api_status():
    """Check Dhan API status and provide debugging information"""
    try:
        # Test endpoint
        response = requests.get(f"{DHAN_API_BASE}/health", timeout=5)
        status = response.status_code
        
        return jsonify({
            "status": status,
            "base_url": DHAN_API_BASE,
            "message": "API status check completed"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "base_url": DHAN_API_BASE
        }), 500

# Indian Market Data API Endpoints for Dhan
@dhan_bp.route('/market-data/historical')
def dhan_historical_data():
    """Fetch historical data from Dhan for Indian stocks"""
    symbol = request.args.get('symbol', 'RELIANCE')
    timeframe = request.args.get('timeframe', '1m')  # Default to 1 minute
    exchange = request.args.get('exchange', 'NSE')   # Default to NSE
    user_id = request.args.get('user_id', 'default_user')
    
    # Get custom date range if provided, otherwise use timeframe-based defaults
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    # If no custom dates provided, set timeframe-based defaults
    if not from_date or not to_date:
        from_date, to_date = get_timeframe_based_dates(timeframe)
    
    if not is_dhan_authenticated(user_id):
        return jsonify({"error": "Dhan not authenticated"}), 401
    
    try:
        access_token = get_dhan_access_token(user_id)
        
        headers = {
            "access-token": access_token,
            "Content-Type": "application/json"
        }
        
        # Get instrument data for the symbol
        from .dhan_utils import realtime_service
        instrument_data = realtime_service.get_instrument_data(symbol)
        
        # Validate parameters
        is_valid, error_msg = validate_trading_params(exchange, timeframe)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Use the first instrument from the list
        if instrument_data and instrument_data.get('InstrumentList'):
            instrument = instrument_data['InstrumentList'][0]
            security_id = instrument['SecurityId']
            exchange_segment = instrument['ExchangeSegment']
        else:
            # Default to RELIANCE if symbol not found
            security_id = "1333"
            exchange_segment = get_dhan_exchange_segment(exchange)
        
        # Get instrument type
        instrument_type = instrument_data.get('instrument_type', 'EQUITY')
        
        # Map timeframe to Dhan format
        mapped_timeframe = get_dhan_timeframe(timeframe)
        
        # Prepare request payload
        payload = {
            "securityId": security_id,
            "exchangeSegment": exchange_segment,
            "instrument": instrument_type,
            "interval": mapped_timeframe,
            "oi": False,
            "fromDate": from_date,
            "toDate": to_date
        }
        
        # Debug logging (only if DEBUG is enabled)
        if isDebugLogging():
            logger.debug(f"Dhan Historical Data Request: Symbol={symbol}, Exchange={exchange}->{exchange_segment}, Timeframe={timeframe}->{mapped_timeframe}, Payload={payload}")
        
        # Fetch historical data from Dhan API
        response = requests.post(
            "https://api.dhan.co/v2/charts/intraday",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Store market data in Redis
            market_data = {
                'symbol': symbol,
                'from_date': from_date,
                'to_date': to_date,
                'timeframe': timeframe,
                'exchange': exchange,
                'data': data,
                'source': 'dhan'
            }
            redis_db.set_market_data(f"{symbol}_historical_{from_date}_{to_date}_{timeframe}", market_data)
            
            return jsonify(data)
        else:
            return jsonify({"error": f"Dhan API error: {response.status_code}", "response": response.text}), response.status_code
            
    except Exception as e:
        logger.error(f"Dhan historical data fetch failed: {e}")
        return jsonify({"error": f"Failed to fetch data: {str(e)}"}), 500

@dhan_bp.route('/market-data/realtime')
def dhan_realtime_data():
    """Get real-time data from Dhan for Indian stocks using WebSocket service"""
    symbol = request.args.get('symbol', 'RELIANCE')
    
    if not is_dhan_authenticated():
        return jsonify({"error": "Dhan not authenticated"}), 401
    
    try:
        from .dhan_utils import realtime_service
        
        # Start the realtime service if not running
        if not realtime_service.is_running():
            realtime_service.start('default_user')
            time.sleep(2)  # Wait for connection to establish
        
        # Subscribe to the symbol
        realtime_service.subscribe_to_symbol(symbol)
        
        # Get realtime data from Redis
        realtime_data = realtime_service.get_realtime_data(symbol)
        
        if realtime_data:
            return jsonify({
                "success": True,
                "symbol": symbol,
                "data": realtime_data,
                "price": realtime_data.get('price', 0),
                "volume": realtime_data.get('volume', 0),
                "change": realtime_data.get('change', 0),
                "change_percent": realtime_data.get('change_percent', 0),
                "high": realtime_data.get('high', 0),
                "low": realtime_data.get('low', 0),
                "open": realtime_data.get('open', 0),
                "timestamp": realtime_data.get('timestamp', int(time.time())),
                "last_update": realtime_data.get('last_update', time.strftime('%Y-%m-%d %H:%M:%S'))
            })
        else:
            # Fallback to REST API if no WebSocket data
            access_token = dhan_session.get('access_token')
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Fetch real-time data from Dhan API
            response = requests.get(
                f"{DHAN_API_BASE}/quotes?symbol={symbol}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return jsonify(data)
            else:
                return jsonify({"error": f"Dhan API error: {response.status_code}"}), response.status_code
                
    except Exception as e:
        app.logger.error(f"Dhan real-time data fetch failed: {e}")
        return jsonify({"error": f"Failed to fetch data: {str(e)}"}), 500

@dhan_bp.route('/market-data/websocket-status')
def dhan_websocket_status():
    """Get WebSocket connection status"""
    if not is_dhan_authenticated():
        return jsonify({"error": "Dhan not authenticated"}), 401
    
    try:
        from .dhan_utils import realtime_service
        
        status = realtime_service.get_connection_status()
        return jsonify({
            "success": True,
            "websocket_status": status,
            "is_healthy": realtime_service.is_running()
        })
    except Exception as e:
        app.logger.error(f"Error getting WebSocket status: {e}")
        return jsonify({"error": f"Failed to get status: {str(e)}"}), 500

@dhan_bp.route('/market-data/order', methods=['POST'])
def dhan_market_order():
    """Place order for Indian stocks through Dhan"""
    order_data = request.json
    
    if not is_dhan_authenticated():
        return jsonify({"error": "Dhan not authenticated"}), 401
    
    try:
        access_token = dhan_session.get('access_token')
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Place order through Dhan API
        response = requests.post(
            f"{DHAN_API_BASE}/orders",
            headers=headers,
            json=order_data
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({"success": True, "broker": "dhan", "data": data})
        else:
            return jsonify({"error": f"Dhan API error: {response.status_code}"}), response.status_code
            
    except Exception as e:
        logger.error(f"Dhan order placement failed: {e}")
        return jsonify({"error": f"Failed to place order: {str(e)}"}), 500

@dhan_bp.route('/market-data/account')
def dhan_account_info():
    """Get account information from Dhan"""
    if not is_dhan_authenticated():
        return jsonify({"error": "Dhan not authenticated"}), 401
    
    try:
        access_token = dhan_session.get('access_token')
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Get account information from Dhan API
        response = requests.get(
            f"{DHAN_API_BASE}/account",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        else:
            return jsonify({"error": f"Dhan API error: {response.status_code}"}), response.status_code
            
    except Exception as e:
        logger.error(f"Dhan account info fetch failed: {e}")
        return jsonify({"error": f"Failed to fetch account info: {str(e)}"}), 500

@dhan_bp.route('/market-data/positions')
def dhan_positions():
    """Get current positions from Dhan"""
    if not is_dhan_authenticated():
        return jsonify({"error": "Dhan not authenticated"}), 401
    
    try:
        access_token = dhan_session.get('access_token')
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Get positions from Dhan API
        response = requests.get(
            f"{DHAN_API_BASE}/positions",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        else:
            return jsonify({"error": f"Dhan API error: {response.status_code}"}), response.status_code
            
    except Exception as e:
        logger.error(f"Dhan positions fetch failed: {e}")
        return jsonify({"error": f"Failed to fetch positions: {str(e)}"}), 500

@dhan_bp.route('/market-data/orders')
def dhan_orders():
    """Get open orders from Dhan"""
    if not is_dhan_authenticated():
        return jsonify({"error": "Dhan not authenticated"}), 401
    
    try:
        access_token = dhan_session.get('access_token')
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Get open orders from Dhan API
        response = requests.get(
            f"{DHAN_API_BASE}/orders",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        else:
            return jsonify({"error": f"Dhan API error: {response.status_code}"}), response.status_code
            
    except Exception as e:
        logger.error(f"Dhan orders fetch failed: {e}")
        return jsonify({"error": f"Failed to fetch orders: {str(e)}"}), 500

@dhan_bp.route('/market-data/exchanges')
def dhan_exchanges():
    """Get available exchanges for Dhan trading"""
    return jsonify({
        "success": True,
        "exchanges": EXCHANGE_MAP,
        "exchange_list": get_exchange_options()
    })

@dhan_bp.route('/market-data/timeframes')
def dhan_timeframes():
    """Get available time frames for Dhan trading"""
    return jsonify({
        "success": True,
        "timeframes": TIMEFRAME_MAP,
        "timeframe_list": get_timeframe_options()
    })

@dhan_bp.route('/market-data/trading-options')
def dhan_trading_options():
    """Get all trading options including exchanges and timeframes for dropdowns"""
    return jsonify({
        "success": True,
        "exchanges": EXCHANGE_MAP,
        "timeframes": TIMEFRAME_MAP,
        "exchange_options": get_exchange_options(),
        "timeframe_options": get_timeframe_options(),
        "interval_options": get_interval_options()
    })

@dhan_bp.route('/market-data/symbols')
def dhan_symbols():
    """Get available symbols for a specific exchange"""
    exchange = request.args.get('exchange', 'NSE')
    user_id = request.args.get('user_id', 'default_user')
    
    if not is_dhan_authenticated(user_id):
        return jsonify({"error": "Dhan not authenticated"}), 401
    
    # Validate exchange
    if exchange not in EXCHANGE_MAP:
        return jsonify({"error": f"Invalid exchange: {exchange}"}), 400
    
    try:
        access_token = get_dhan_access_token(user_id)
        
        headers = {
            "access-token": access_token,
            "Content-Type": "application/json"
        }
        
        # Get symbols for the specified exchange
        exchange_segment = get_dhan_exchange_segment(exchange)
        
        # Fetch symbols from Dhan API
        response = requests.get(
            f"https://api.dhan.co/v2/instruments/{exchange_segment}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Format symbols for dropdown
            symbols = []
            if data.get('data'):
                for instrument in data['data']:
                    symbols.append({
                        "value": instrument.get('tradingSymbol', ''),
                        "label": f"{instrument.get('tradingSymbol', '')} - {instrument.get('instrumentName', '')}",
                        "security_id": instrument.get('securityId', ''),
                        "exchange_segment": instrument.get('exchangeSegment', ''),
                        "instrument_type": instrument.get('instrumentType', '')
                    })
            
            return jsonify({
                "success": True,
                "exchange": exchange,
                "exchange_segment": exchange_segment,
                "symbols": symbols,
                "count": len(symbols)
            })
        else:
            return jsonify({"error": f"Dhan API error: {response.status_code}"}), response.status_code
            
    except Exception as e:
        logger.error(f"Dhan symbols fetch failed: {e}")
        return jsonify({"error": f"Failed to fetch symbols: {str(e)}"}), 500

@dhan_bp.route('/market-data/test-timeframe')
def dhan_test_timeframe():
    """Test endpoint to verify timeframe mapping and API calls"""
    symbol = request.args.get('symbol', 'RELIANCE')
    timeframe = request.args.get('timeframe', '1m')
    exchange = request.args.get('exchange', 'NSE')
    user_id = request.args.get('user_id', 'default_user')
    
    # Get custom date range if provided, otherwise use timeframe-based defaults
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    # If no custom dates provided, set timeframe-based defaults
    if not from_date or not to_date:
        from_date, to_date = get_timeframe_based_dates(timeframe)
    
    if not is_dhan_authenticated(user_id):
        return jsonify({"error": "Dhan not authenticated"}), 401
    
    try:
        access_token = get_dhan_access_token(user_id)
        
        headers = {
            "access-token": access_token,
            "Content-Type": "application/json"
        }
        
        # Validate parameters
        is_valid, error_msg = validate_trading_params(exchange, timeframe)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Get mapped values
        exchange_segment = get_dhan_exchange_segment(exchange)
        mapped_timeframe = get_dhan_timeframe(timeframe)
        
        # Test payload
        payload = {
            "securityId": "1333",  # RELIANCE
            "exchangeSegment": exchange_segment,
            "instrument": "EQUITY",
            "interval": mapped_timeframe,
            "oi": False,
            "fromDate": from_date,
            "toDate": to_date
        }
        
        if isDebugLogging():
            logger.debug(f"Test Timeframe Request: Original timeframe={timeframe}, Mapped timeframe={mapped_timeframe}, Payload={payload}")
        
        # Make API call
        response = requests.post(
            "https://api.dhan.co/v2/charts/intraday",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                "success": True,
                "original_timeframe": timeframe,
                "mapped_timeframe": mapped_timeframe,
                "exchange": exchange,
                "exchange_segment": exchange_segment,
                "payload": payload,
                "response_status": response.status_code,
                "data_points": len(data.get('data', [])),
                "data": data
            })
        else:
            return jsonify({
                "error": f"Dhan API error: {response.status_code}",
                "response": response.text,
                "payload": payload,
                "original_timeframe": timeframe,
                "mapped_timeframe": mapped_timeframe
            }), response.status_code
            
    except Exception as e:
        logger.error(f"Dhan test timeframe failed: {e}")
        return jsonify({"error": f"Failed to test timeframe: {str(e)}"}), 500

@dhan_bp.route('/market-data/intraday')
def dhan_intraday_data():
    """Fetch intraday data from Dhan - maps interval parameter to timeframe"""
    symbol = request.args.get('symbol', 'RELIANCE')
    interval = request.args.get('interval', '1m')  # Frontend sends 'interval'
    exchange = request.args.get('exchange', 'NSE')
    user_id = request.args.get('user_id', 'default_user')
    
    # Map interval to timeframe using common utility
    timeframe = map_interval_to_timeframe(interval)
    
    if isDebugLogging():
        logger.debug(f"📊 Intraday Request: interval={interval} -> timeframe={timeframe}")
    
    # Get custom date range if provided, otherwise use timeframe-based defaults
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    # If no custom dates provided, set timeframe-based defaults
    if not from_date or not to_date:
        from_date, to_date = get_timeframe_based_dates(timeframe)
    
    if not is_dhan_authenticated(user_id):
        return jsonify({"error": "Dhan not authenticated"}), 401
    
    try:
        access_token = get_dhan_access_token(user_id)
        
        headers = {
            "access-token": access_token,
            "Content-Type": "application/json"
        }
        
        # Validate parameters
        is_valid, error_msg = validate_trading_params(exchange, timeframe)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        # Get instrument data for the symbol
        from .dhan_utils import realtime_service
        instrument_data = realtime_service.get_instrument_data(symbol)
        
        # Use the first instrument from the list
        if instrument_data and instrument_data.get('InstrumentList'):
            instrument = instrument_data['InstrumentList'][0]
            security_id = instrument['SecurityId']
            exchange_segment = instrument['ExchangeSegment']
        else:
            # Default to RELIANCE if symbol not found
            security_id = "1333"
            exchange_segment = get_dhan_exchange_segment(exchange)
        
        # Get instrument type
        instrument_type = instrument_data.get('instrument_type', 'EQUITY')
        
        # Map timeframe to Dhan format
        mapped_timeframe = get_dhan_timeframe(timeframe)
        
        # Prepare request payload
        payload = {
            "securityId": security_id,
            "exchangeSegment": exchange_segment,
            "instrument": instrument_type,
            "interval": mapped_timeframe,
            "oi": False,
            "fromDate": from_date,
            "toDate": to_date
        }
        
        # Debug logging (only if DEBUG is enabled)
        if isDebugLogging():
            logger.debug(f"Dhan Intraday Request: Symbol={symbol}, Interval={interval}->Timeframe={timeframe}->Mapped={mapped_timeframe}, Exchange={exchange}->{exchange_segment}, Payload={payload}")
        
        # Fetch historical data from Dhan API
        response = requests.post(
            "https://api.dhan.co/v2/charts/intraday",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Store market data in Redis
            market_data = {
                'symbol': symbol,
                'interval': interval,
                'timeframe': timeframe,
                'from_date': from_date,
                'to_date': to_date,
                'exchange': exchange,
                'data': data,
                'source': 'dhan'
            }
            redis_db.set_market_data(f"{symbol}_intraday_{interval}_{from_date}_{to_date}", market_data)
            
            return jsonify(data)
        else:
            return jsonify({"error": f"Dhan API error: {response.status_code}", "response": response.text}), response.status_code
            
    except Exception as e:
        logger.error(f"Dhan intraday data fetch failed: {e}")
        return jsonify({"error": f"Failed to fetch data: {str(e)}"}), 500

@dhan_bp.route('/market-data/timeframe-ranges')
def dhan_timeframe_ranges():
    """Get timeframe-based date ranges for reference"""
    ranges_info = get_timeframe_ranges_info()
    
    return jsonify({
        "success": True,
        **ranges_info
    })