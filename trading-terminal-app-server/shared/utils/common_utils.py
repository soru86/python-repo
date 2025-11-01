import os
import random
import base64

def generate_unique_user_id():
    return random.randint(10000, 99999)

def text_to_base64(value):
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")

def base64_to_text(value):
    return base64.b64decode(value).decode("utf-8")

def get_supported_auth_types():
    return ['google', 'facebook', 'basic']

def isDebugLogging():
    return (
        os.environ.get('FLASK_ENV') == 'development'
        or os.environ.get('LOG_LEVEL', 'INFO').lower() == 'debug'
        or os.environ.get('DEBUG', 'False').lower() == 'true'
    )

def isErrorLogging():
    return (
        os.environ.get('FLASK_ENV') == 'development'
        or os.environ.get('LOG_LEVEL', 'INFO').lower() == 'error'
        or os.environ.get('DEBUG', 'False').lower() == 'false'
    )

def isInfoLogging():
    return (
        os.environ.get('FLASK_ENV') == 'development'
        or os.environ.get('LOG_LEVEL', 'INFO').lower() == 'info'
        or os.environ.get('DEBUG', 'False').lower() == 'false'
    )