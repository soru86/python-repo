import requests
import urllib.parse
import hashlib
import json
from . import fyers_bp
from shared.config.config import get_config
from app import flask_app
from flask import jsonify, request, redirect, session, current_app
from blueprints.indian_market.fyers.fyers_utils import is_fyers_authenticated

# Get config from current app context or use default
def get_fyers_api_base():
    try:
        return current_app.config.get('FYERS_API_BASE') or flask_app.config.get('FYERS_API_BASE')
    except:
        return None

def get_fyers_api_v3_base():
    try:
        return current_app.config.get('FYERS_API_V3_BASE') or flask_app.config.get('FYERS_API_V3_BASE')
    except:
        return None

FYERS_API_BASE = get_fyers_api_base()
FYERS_API_V3_BASE = get_fyers_api_v3_base()

@fyers_bp.route('/login')
def fyers_login():
    """Initiate Fyers OAuth flow"""
    client_id = request.args.get('client_id')
    secret_key = request.args.get('secret_key')
    redirect_uri = request.args.get('redirect_uri', 'http://localhost:8000/fyers/callback')
    
    if not client_id or not secret_key:
        return jsonify({"error": "Missing client_id or secret_key"}), 400
    
    # Store credentials in session
    session['fyers_client_id'] = client_id
    session['fyers_secret_key'] = secret_key
    session['fyers_redirect_uri'] = redirect_uri

    print("Session set in /fyers/login:", session.get('fyers_client_id'), session.get('fyers_secret_key'), session.get('fyers_redirect_uri'))

    # Redirect to Fyers authorization page
    fyers_auth_url = (
        f"https://api-t1.fyers.in/api/v3/generate-authcode?"
        f"client_id={client_id}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri, safe='')}&"
        f"response_type=code&"
        f"state=None"
    )
    
    return redirect(fyers_auth_url)

@fyers_bp.route('/callback')
def fyers_callback():
    """Handle Fyers OAuth callback"""
    print("---- /fyers/callback called ----")
    auth_code = request.args.get('auth_code')

    if not auth_code:
        return jsonify({"error": "Authorization failed - no code received"}), 400

    client_id = session.get('fyers_client_id')
    secret_key = session.get('fyers_secret_key')
    redirect_uri = session.get('fyers_redirect_uri')

    print("Session in /fyers/callback:", client_id, secret_key, redirect_uri)

    if not all([client_id, secret_key, redirect_uri]):
        return jsonify({"error": "Missing session credentials"}), 400

    # Compute appIdHash as SHA-256 of "client_id:secret_key"
    app_id_hash_input = f"{client_id}:{secret_key}"
    app_id_hash = hashlib.sha256(app_id_hash_input.encode()).hexdigest()

    payload = {
        "grant_type": "authorization_code",
        "appIdHash": app_id_hash,
        "code": auth_code
    }

    try:
        print(f"Making token request to: {FYERS_API_BASE}/api/v3/validate-authcode")
        print(f"Payload: {payload}")
        
        response = requests.post(f"{FYERS_API_BASE}/api/v3/validate-authcode", json=payload)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        
        data = response.json()
        print(f"Response data: {data}")

        if data.get("access_token"):
            # Store in global session (in production, use proper session management)
            fyers_session['access_token'] = data["access_token"]
            fyers_session['client_id'] = client_id
            fyers_session['code'] = auth_code
            
            # Get user profile - Updated to APIv3
            access_token = data["access_token"]
            refresh_token = data["refresh_token"]

            headers = {
                "Authorization": f"{client_id}:{access_token}",
                "validation": refresh_token
            }
            
            # Try to get user profile, but don't fail if it doesn't work
            profile_info = {
                'name': f"User ({client_id})",
                'client_id': client_id
            }
            
            try:
                print(f"Making profile request to: {FYERS_API_V3_BASE}/api/v3/profile")
                profile_response = requests.get(f"{FYERS_API_V3_BASE}/api/v3/profile", headers=headers)
                profile_data = profile_response.json()
                print(f"Profile response: {profile_data}")
                
                # Extract profile data with better error handling
                if profile_data.get('s') == 'ok' and profile_data.get('data'):
                    profile_info = profile_data.get('data', profile_info)
                elif profile_data.get('data'):
                    profile_info = profile_data.get('data', profile_info)
                else:
                    # Use fallback profile info
                    profile_info.update({
                        'email': profile_data.get('email', ''),
                        'mobile': profile_data.get('mobile', ''),
                        'pan': profile_data.get('pan', '')
                    })
            except Exception as profile_error:
                print(f"Profile request failed, using fallback: {profile_error}")
                # Continue with fallback profile info
            
            fyers_session['profile'] = profile_info
            
            # Return HTML page that closes the popup and communicates with parent
            success_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Fyers Authentication Success</title>
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
                    .spinner {{
                        border: 4px solid #f3f3f3;
                        border-top: 4px solid #10b981;
                        border-radius: 50%;
                        width: 32px;
                        height: 32px;
                        animation: spin 1s linear infinite;
                        margin: 20px auto;
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
                    <p>Successfully connected to Fyers.</p>
                    <div class="spinner"></div>
                    <p><b>Please wait...</b> Finalizing authentication. This window will close automatically.</p>
                </div>
                <script>
                    // Send message to parent window
                    if (window.opener) {{
                        window.opener.postMessage({{
                            type: 'fyers_auth_success',
                            data: {{
                                success: true,
                                message: 'Successfully authenticated with Fyers',
                                access_token: '{data["access_token"]}',
                                profile: {json.dumps(profile_info)}
                            }}
                        }}, '*');
                    }}
                    setTimeout(() => {{ window.close(); }}, 2000);
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
                <title>Fyers Authentication Failed</title>
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
                            type: 'fyers_auth_error',
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

@fyers_bp.route('/status')
def fyers_status():
    """Check Fyers authentication status"""
    access_token = fyers_session.get('access_token')

    if not access_token:
        return jsonify({
            "isLoggedIn": False,
            "message": "Not authenticated"
        })
    
    return jsonify({
        "isLoggedIn": True,
        "accessToken": access_token,
        "profile": fyers_session.get('profile', {}),
        "client_id": fyers_session.get('client_id')
    })

@fyers_bp.route('/logout')
def fyers_logout():
    """Logout from Fyers"""
    global fyers_session
    fyers_session = {}
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})

@fyers_bp.route('/api-status')
def fyers_api_status():
    """Check Fyers API status and provide debugging information"""
    try:
        # Test v3 endpoint
        v3_response = requests.get(f"{FYERS_API_V3_BASE}/api/v3/profile", timeout=5)
        v3_status = v3_response.status_code
        
        return jsonify({
            "v3_status": v3_status,
            "v3_base_url": FYERS_API_V3_BASE,
            "message": "API status check completed"
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "v3_base_url": FYERS_API_V3_BASE
        }), 500

@fyers_bp.route('/place_order', methods=['POST'])
def fyers_place_order():
    """Place trading order through Fyers"""
    access_token = fyers_session.get('access_token')
    
    if not access_token:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        order_data = request.json
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Default order payload
        order_payload = {
            "symbol": order_data.get('symbol', 'NSE:RELIANCE-EQ'),
            "qty": order_data.get('quantity', 1),
            "type": order_data.get('type', 2),      # market order
            "side": order_data.get('side', 1),      # buy
            "productType": order_data.get('productType', 'INTRADAY'),
            "limitPrice": order_data.get('limitPrice', 0),
            "stopPrice": order_data.get('stopPrice', 0),
            "validity": order_data.get('validity', 'DAY'),
            "disclosedQty": order_data.get('disclosedQty', 0),
            "offlineOrder": order_data.get('offlineOrder', False),
            "exchange": order_data.get('exchange', 'NSE'),
            "segment": order_data.get('segment', 'EQUITY')
        }
        
        response = requests.post(f"{FYERS_API_V3_BASE}/api/v3/orders", headers=headers, json=order_payload)
        result = response.json()
        
        return jsonify({
            "success": True,
            "order_response": result
        })
        
    except Exception as e:
        return jsonify({"error": f"Order placement failed: {str(e)}"}), 500

# Indian Market Data API Endpoints for Fyers
@fyers_bp.route('/market-data/historical')
def fyers_historical_data():
    """Fetch historical data from Fyers for Indian stocks"""
    symbol = request.args.get('symbol', 'RELIANCE')
    interval = request.args.get('interval', '1h')
    
    if not is_fyers_authenticated():
        return jsonify({"error": "Fyers not authenticated"}), 401
    
    try:
        access_token = fyers_session.get('access_token')
        client_id = fyers_session.get('client_id')
        
        headers = {
            "Authorization": f"{client_id}:{access_token}",
            "Content-Type": "application/json"
        }
        
        # Fetch historical data from Fyers APIv3
        # Note: This is a placeholder - actual Fyers API endpoint may differ
        response = requests.get(
            f"{FYERS_API_V3_BASE}/api/v3/history?symbol={symbol}&resolution={interval}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        else:
            return jsonify({"error": f"Fyers API error: {response.status_code}"}), response.status_code
            
    except Exception as e:
        print(f"Fyers historical data fetch failed: {e}")
        return jsonify({"error": f"Failed to fetch data: {str(e)}"}), 500

@fyers_bp.route('/market-data/realtime')
def fyers_realtime_data():
    """Get real-time data from Fyers for Indian stocks"""
    symbol = request.args.get('symbol', 'RELIANCE')
    
    if not is_fyers_authenticated():
        return jsonify({"error": "Fyers not authenticated"}), 401
    
    try:
        access_token = fyers_session.get('access_token')
        client_id = fyers_session.get('client_id')
        
        headers = {
            "Authorization": f"{client_id}:{access_token}",
            "Content-Type": "application/json"
        }
        
        # Fetch real-time data from Fyers APIv3
        response = requests.get(
            f"{FYERS_API_V3_BASE}/api/v3/quotes?symbols={symbol}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        else:
            return jsonify({"error": f"Fyers API error: {response.status_code}"}), response.status_code
            
    except Exception as e:
        print(f"Fyers real-time data fetch failed: {e}")
        return jsonify({"error": f"Failed to fetch data: {str(e)}"}), 500

@fyers_bp.route('/market-data/order', methods=['POST'])
def fyers_market_order():
    """Place order for Indian stocks through Fyers"""
    order_data = request.json
    
    if not is_fyers_authenticated():
        return jsonify({"error": "Fyers not authenticated"}), 401
    
    try:
        access_token = fyers_session.get('access_token')
        client_id = fyers_session.get('client_id')
        
        headers = {
            "Authorization": f"{client_id}:{access_token}",
            "Content-Type": "application/json"
        }
        
        # Place order through Fyers APIv3
        response = requests.post(
            f"{FYERS_API_V3_BASE}/api/v3/orders",
            headers=headers,
            json=order_data
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify({"success": True, "broker": "fyers", "data": data})
        else:
            return jsonify({"error": f"Fyers API error: {response.status_code}"}), response.status_code
            
    except Exception as e:
        print(f"Fyers order placement failed: {e}")
        return jsonify({"error": f"Failed to place order: {str(e)}"}), 500

@fyers_bp.route('/market-data/account')
def fyers_account_info():
    """Get account information from Fyers"""
    if not is_fyers_authenticated():
        return jsonify({"error": "Fyers not authenticated"}), 401
    
    try:
        access_token = fyers_session.get('access_token')
        client_id = fyers_session.get('client_id')
        
        headers = {
            "Authorization": f"{client_id}:{access_token}",
            "Content-Type": "application/json"
        }
        
        # Get account information from Fyers APIv3
        response = requests.get(
            f"{FYERS_API_V3_BASE}/api/v3/account",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        else:
            return jsonify({"error": f"Fyers API error: {response.status_code}"}), response.status_code
            
    except Exception as e:
        print(f"Fyers account info fetch failed: {e}")
        return jsonify({"error": f"Failed to fetch account info: {str(e)}"}), 500

@fyers_bp.route('/market-data/positions')
def fyers_positions():
    """Get current positions from Fyers"""
    if not is_fyers_authenticated():
        return jsonify({"error": "Fyers not authenticated"}), 401
    
    try:
        access_token = fyers_session.get('access_token')
        client_id = fyers_session.get('client_id')
        
        headers = {
            "Authorization": f"{client_id}:{access_token}",
            "Content-Type": "application/json"
        }
        
        # Get positions from Fyers APIv3
        response = requests.get(
            f"{FYERS_API_V3_BASE}/api/v3/positions",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        else:
            return jsonify({"error": f"Fyers API error: {response.status_code}"}), response.status_code
            
    except Exception as e:
        print(f"Fyers positions fetch failed: {e}")
        return jsonify({"error": f"Failed to fetch positions: {str(e)}"}), 500

@fyers_bp.route('/market-data/orders')
def fyers_orders():
    """Get open orders from Fyers"""
    if not is_fyers_authenticated():
        return jsonify({"error": "Fyers not authenticated"}), 401
    
    try:
        access_token = fyers_session.get('access_token')
        client_id = fyers_session.get('client_id')
        
        headers = {
            "Authorization": f"{client_id}:{access_token}",
            "Content-Type": "application/json"
        }
        
        # Get open orders from Fyers APIv3
        response = requests.get(
            f"{FYERS_API_V3_BASE}/api/v3/orders",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return jsonify(data)
        else:
            return jsonify({"error": f"Fyers API error: {response.status_code}"}), response.status_code
            
    except Exception as e:
        print(f"Fyers orders fetch failed: {e}")
        return jsonify({"error": f"Failed to fetch orders: {str(e)}"}), 500 