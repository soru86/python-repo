from flask import Blueprint
from blueprints.indian_market.dhan.routes import dhan_bp
from blueprints.indian_market.fyers.routes import fyers_bp

# Create Blueprint for Indian routes
indian_market_bp = Blueprint('indian_market', __name__)
indian_market_bp.register_blueprint(dhan_bp)
indian_market_bp.register_blueprint(fyers_bp)
