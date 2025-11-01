import os
import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = False
    TESTING = False
    
    # Server Configuration
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 8000))
    WORKERS = int(os.environ.get('WORKERS', 4))
    
    # Redis Configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    
    # Session Configuration
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_REDIS = redis.from_url(REDIS_URL)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
    SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
    
    # CORS Configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000').split(',')
    
    # API Keys
    BINANCE_API_KEY = os.environ.get('BINANCE_API_KEY')
    BINANCE_API_SECRET = os.environ.get('BINANCE_API_SECRET')
    

    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = os.environ.get('LOG_FORMAT', 'json')
    
    # Rate Limiting
    RATE_LIMIT_DEFAULT = os.environ.get('RATE_LIMIT_DEFAULT', '100 per minute')
    RATE_LIMIT_STORAGE_URL = os.environ.get('RATE_LIMIT_STORAGE_URL', 'redis://localhost:6379/1')
    
    # Sentry Configuration
    SENTRY_DSN = os.environ.get('SENTRY_DSN')
    
    # Base URL for broker requests
    BASE_URL = os.environ.get('BASE_URL', 'http://127.0.0.1:8000')

    # Dhan API configuration
    DHAN_API_BASE = "https://api.dhan.co"

    # Fyers API configuration - Updated to APIv3
    FYERS_API_BASE = "https://api-t1.fyers.in"
    FYERS_API_V3_BASE = "https://api-t1.fyers.in"

    # Binance API Configuration
    BINANCE_API_KEY = "binance_key"
    BINANCE_API_SECRET = "binance_secret"

    # Mongo DB Configuration
    MONGO_URI = "mongodb://localhost:27017/app_db?retryWrites=true"

    # Google OAuth Configuration
    # alg.trd.oauth@gmail.com
    # Pass: ClipperClamper@2025
    GOOGLE_CLIENT_ID="77222803445-e8d8m3k8vart24a7tln3e88ft7pl3ie0.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET="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"
    GOOGLE_REQUEST_TOKEN_URL="https://accounts.google.com/o/oauth2/v2/auth"
    FRONTEND_URL="http://localhost:5173/landing"

    # Facebook OAuth Configuration
    FACEBOOK_CLIENT_ID=""
    FACEBOOK_CLIENT_SECRET=""
    FACEBOOK_REQUEST_TOKEN_URL=""

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    SESSION_COOKIE_SECURE = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(envName: str):
    """Get configuration based on environment"""
    if not envName:
        env = os.environ.get('FLASK_ENV', 'development')
        return config.get(env, config['default'])
    else:
        env = os.environ.get('FLASK_ENV', envName)
        return config.get(env, config[envName]) 