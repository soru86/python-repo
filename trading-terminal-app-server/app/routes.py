import redis
from app import flask_app
from flask import jsonify
from datetime import datetime
from blueprints.algo_routes import init_algo_routes

@flask_app.route('/')
def home():
    return "App server is running on port 8000!"

# Health check endpoint
@flask_app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check Redis connection
        redis_client = redis.from_url(flask_app.config['REDIS_URL'])
        redis_client.ping()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            # 'environment': config_name,
            'version': '1.0.0'
        })
    except Exception as e:
        flask_app.logger.error("Health check failed", error=str(e))
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# API documentation endpoint
@flask_app.route('/api/docs')
def api_docs():
    """API documentation endpoint"""
    return jsonify({
        'title': 'Trading API Documentation',
        'version': '1.0.0',
        'endpoints': {
            'health': {
                'method': 'GET',
                'path': '/health',
                'description': 'Health check endpoint'
            },
            'indian_market_data': {
                'method': 'GET',
                'path': '/indian-market',
                'description': 'Get Indian market data from authenticated brokers',
                'query_params': {
                    'symbol': 'string',
                    'interval': 'string'
                }
            },
            'algo_health': {
                'method': 'GET',
                'path': '/api/algo/health',
                'description': 'Algorithmic trading system health check'
            },
            'algo_strategies': {
                'method': 'GET',
                'path': '/api/algo/strategies',
                'description': 'Get all deployed trading strategies'
            },
            'deploy_strategy': {
                'method': 'POST',
                'path': '/api/algo/strategies',
                'description': 'Deploy a new trading strategy'
            },
            'strategy_status': {
                'method': 'GET',
                'path': '/api/algo/strategies/<name>',
                'description': 'Get status of a specific strategy'
            },
            'strategy_logs': {
                'method': 'GET',
                'path': '/api/algo/strategies/<name>/logs',
                'description': 'Get logs for a specific strategy'
            },
            'restart_strategy': {
                'method': 'POST',
                'path': '/api/algo/strategies/<name>/restart',
                'description': 'Restart a specific strategy'
            },
            'stop_strategy': {
                'method': 'POST',
                'path': '/api/algo/strategies/<name>/stop',
                'description': 'Stop a specific strategy'
            },
            'performance_metrics': {
                'method': 'GET',
                'path': '/api/algo/performance',
                'description': 'Get performance metrics for all strategies'
            },
            'strategy_templates': {
                'method': 'GET',
                'path': '/api/algo/templates',
                'description': 'Get available strategy templates'
            }
        }
    })

# Initialize algorithmic trading routes
init_algo_routes(flask_app)
