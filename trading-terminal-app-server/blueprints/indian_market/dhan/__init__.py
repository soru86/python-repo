from flask import Blueprint

# Create Blueprint for Dhan routes
dhan_bp = Blueprint('dhan', __name__, url_prefix='/dhan')

dhan_session = {} 