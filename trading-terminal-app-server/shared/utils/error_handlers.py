import traceback
from flask import jsonify, request
from werkzeug.exceptions import HTTPException
from .logger import get_logger

logger = get_logger(__name__)

class APIError(Exception):
    """Custom API error class"""
    def __init__(self, message, status_code=400, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['error'] = self.message
        rv['status_code'] = self.status_code
        return rv

def handle_api_error(error):
    """Handle API errors"""
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

def handle_http_error(error):
    """Handle HTTP errors"""
    response = jsonify({
        'error': error.description,
        'status_code': error.code
    })
    response.status_code = error.code
    return response

def handle_generic_error(error):
    """Handle generic errors"""
    logger.error("Unhandled error", 
                error=str(error), 
                traceback=traceback.format_exc(),
                request_path=request.path,
                request_method=request.method,
                user_agent=request.headers.get('User-Agent'))
    
    response = jsonify({
        'error': 'Internal server error',
        'status_code': 500
    })
    response.status_code = 500
    return response

def register_error_handlers(app):
    """Register error handlers with Flask app"""
    app.register_error_handler(APIError, handle_api_error)
    app.register_error_handler(HTTPException, handle_http_error)
    app.register_error_handler(Exception, handle_generic_error) 