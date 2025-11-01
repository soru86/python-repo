from flask import Blueprint
from blueprints.oauth.google.routes import google_oauth_bp
from blueprints.oauth.facebook import facebook_oauth_bp


# Create Blueprint for Indian routes
oauth_bp = Blueprint('oauth', __name__)
oauth_bp.register_blueprint(google_oauth_bp)
oauth_bp.register_blueprint(facebook_oauth_bp)
