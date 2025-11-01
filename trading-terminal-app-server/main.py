from app import flask_app
from blueprints.indian_market.routes import indian_market_bp
from blueprints.crypto_market import crypto_market_bp
from blueprints.oauth import oauth_bp
from blueprints.signup.routes.routes import signup_bp
from blueprints.basic_auth.routes.routes import basic_auth_bp
from shared.utils.db import mongo_db

def setup_app(flask_app):
    flask_app.register_blueprint(indian_market_bp, url_prefix='/indian-market')
    flask_app.register_blueprint(crypto_market_bp, url_prefix='/crypto-market')
    flask_app.register_blueprint(oauth_bp, url_prefix='/oauth')
    flask_app.register_blueprint(signup_bp, url_prefix='/users')
    flask_app.register_blueprint(basic_auth_bp, url_prefix='/basic-auth')
    return flask_app

flask_app = setup_app(flask_app)

# WSGI application entry point for Gunicorn
application = flask_app
