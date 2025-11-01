from flask import Blueprint
from blueprints.crypto_market.binance.routes import binance_bp

# Create Blueprint for Crypto routes
crypto_market_bp = Blueprint('crypto_market', __name__)
crypto_market_bp.register_blueprint(binance_bp)
