from flask import Blueprint

# Create Blueprint for binance routes
binance_bp = Blueprint('binance', __name__, url_prefix='/binance')

binance_session = {} 