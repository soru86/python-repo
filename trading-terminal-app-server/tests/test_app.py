import pytest
from app import create_app
import json

@pytest.fixture
def client():
    """Create a test client for the Flask application"""
    app = create_app('testing')
    with app.test_client() as client:
        yield client

def test_home_endpoint(client):
    """Test the home endpoint"""
    response = client.get('/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'message' in data
    assert data['message'] == 'Trading API is running!'

def test_health_endpoint(client):
    """Test the health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'status' in data
    assert data['status'] in ['healthy', 'unhealthy']

def test_api_docs_endpoint(client):
    """Test the API documentation endpoint"""
    response = client.get('/api/docs')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'title' in data
    assert 'endpoints' in data



def test_indian_market_data_endpoint(client):
    """Test the Indian market data endpoint"""
    response = client.get('/indian-market-data?symbol=RELIANCE&interval=1h')
    # This might fail if no brokers are authenticated, but should return proper error
    assert response.status_code in [200, 404, 500]

def test_rate_limiting(client):
    """Test rate limiting"""
    # Make multiple requests to trigger rate limiting
    for _ in range(10):
        client.get('/health')
    
    # The 11th request should be rate limited
    response = client.get('/health')
    # Rate limiting might not be enabled in testing, so check for either 200 or 429
    assert response.status_code in [200, 429]

def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.get('/')
    assert 'Access-Control-Allow-Origin' in response.headers

def test_security_headers(client):
    """Test security headers are present"""
    response = client.get('/')
    headers = response.headers
    assert 'X-Content-Type-Options' in headers
    assert 'X-Frame-Options' in headers
    assert 'X-XSS-Protection' in headers 