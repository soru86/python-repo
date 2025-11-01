import time
from flask import request, g, jsonify
from functools import wraps
from .logger import get_logger

logger = get_logger(__name__)

def log_request_info():
    """Log request information"""
    g.start_time = time.time()
    logger.info("Request started",
                method=request.method,
                path=request.path,
                ip=request.remote_addr,
                user_agent=request.headers.get('User-Agent'))

def log_response_info(response):
    """Log response information"""
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        logger.info("Request completed",
                    method=request.method,
                    path=request.path,
                    status_code=response.status_code,
                    duration=duration)
    return response

def require_api_key(f):
    """Decorator to require API key for protected endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        # In production, validate against database or environment
        valid_keys = ['your-api-key-here']  # Replace with actual validation
        if api_key not in valid_keys:
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def validate_json_content_type(f):
    """Decorator to validate JSON content type"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'PATCH']:
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
        return f(*args, **kwargs)
    return decorated_function

def add_security_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response

def setup_middleware(app):
    """Setup middleware for the Flask app"""
    app.before_request(log_request_info)
    app.after_request(log_response_info)
    app.after_request(add_security_headers)
