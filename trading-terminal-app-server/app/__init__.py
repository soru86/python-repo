import os
import redis
from flask import Flask
from flask_cors import CORS
from shared.config.config import get_config
from flask_session import Session
from shared.utils.logger import setup_logging
from flask_pymongo import PyMongo

def add_security_config(app):
    app.secret_key = app.config.get('SECRET_KEY')
    return app

def add_redis_config(app):
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_REDIS'] = redis.from_url('redis://localhost:6379/0')
    app.config['SESSION_COOKIE_SECURE'] = True
    return app

def add_logger_config(app):
    app.logger = setup_logging(
        log_level=app.config.get('LOG_LEVEL', 'INFO'),
        log_format=app.config.get('LOG_FORMAT', 'json')
    )
    return app

def initialize_db(app):
    mongo = PyMongo(app)
    app.mongo = mongo
    return app

def load_config(app):
    return app.config.from_object(get_config(os.environ.get('FLASK_ENV', 'development')))

def add_cors_config(app):
    if app.config.get('FLASK_ENV') == 'development' or app.config.get('DEBUG', False):
        # In development, allow specific origins
        CORS(app, 
             supports_credentials=True, 
             origins=['http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:3000', 'http://127.0.0.1:3000'],
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
             allow_headers=['Content-Type', 'Authorization', 'access-token', 'user-id'],
             expose_headers=['Content-Type', 'Authorization'],
             max_age=3600)
    else:
        # In production, use specific origins
        CORS(app, 
             supports_credentials=True, 
             origins=['http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:3000', 'http://127.0.0.1:3000'],
             methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
             allow_headers=['Content-Type', 'Authorization', 'access-token', 'user-id'],
             expose_headers=['Content-Type', 'Authorization'],
             max_age=3600)
    return app

def create_app():
    flask_app = Flask(__name__)

    # Load configuration
    load_config(flask_app)

    # Configure CORS after configuration is loaded
    add_cors_config(flask_app)
    
    # Set secret key
    add_security_config(flask_app)

    # initialize Mongo DB
    initialize_db(flask_app)

    # Add Redis configuration
    add_redis_config(flask_app)

    # Add Logger Config
    add_logger_config(flask_app)

    # Add server side session
    Session(flask_app)

    return flask_app

flask_app = create_app()
