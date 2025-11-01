from flask import Blueprint

# Create Blueprint for fyers routes
fyers_bp = Blueprint('fyers', __name__, url_prefix='/fyers')

fyers_session = {} 