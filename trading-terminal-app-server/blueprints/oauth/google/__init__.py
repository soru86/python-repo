from flask import Blueprint

# Create Blueprint for Indian routes
google_oauth_bp = Blueprint('google_oauth', __name__, url_prefix='/google')
