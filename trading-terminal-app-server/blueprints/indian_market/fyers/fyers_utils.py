# Additional Fyers-specific functions can be added here
from flask import session
from . import fyers_session

def get_fyers_session():
    """Get current Fyers session data"""
    return fyers_session

def clear_fyers_session():
    """Clear Fyers session data"""
    global fyers_session
    fyers_session = {}

def is_fyers_authenticated():
    """Check if Fyers is authenticated"""
    print(session)
    return 'access_token' in fyers_session and fyers_session['access_token']