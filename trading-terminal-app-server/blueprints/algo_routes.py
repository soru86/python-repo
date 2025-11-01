"""
API Routes for Algorithmic Trading Management

This module provides REST API endpoints for:
- Strategy deployment and management
- Container monitoring and control
- Performance metrics and logs
- Redis Streams management
"""

from flask import Blueprint, request, jsonify
from typing import Dict, List, Any
import logging
import json

from algo.strategy_manager import StrategyManager
from algo.redis_streams import streams_manager
from algo.containers import ContainerManager, ManagerConfig
from algo.containers.strategy_container import ContainerConfig

logger = logging.getLogger(__name__)

# Create blueprint
algo_bp = Blueprint('algo', __name__, url_prefix='/api/algo')

# Global strategy manager instance
strategy_manager = None

def init_strategy_manager():
    """Initialize the strategy manager"""
    global strategy_manager
    if strategy_manager is None:
        strategy_manager = StrategyManager()
        strategy_manager.start()

@algo_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for algorithmic trading system"""
    try:
        if strategy_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'Strategy manager not initialized'
            }), 500
        
        health_status = strategy_manager.get_health_status()
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@algo_bp.route('/strategies', methods=['GET'])
def get_all_strategies():
    """Get all deployed strategies"""
    try:
        if strategy_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'Strategy manager not initialized'
            }), 500
        
        strategies = strategy_manager.get_all_strategies()
        return jsonify(strategies)
        
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@algo_bp.route('/strategies', methods=['POST'])
def deploy_strategy():
    """Deploy a new trading strategy"""
    try:
        if strategy_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'Strategy manager not initialized'
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['strategy_name', 'strategy_type', 'symbols', 'exchange']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Deploy strategy
        success = strategy_manager.deploy_strategy(data)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Strategy {data["strategy_name"]} deployed successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to deploy strategy {data["strategy_name"]}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error deploying strategy: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@algo_bp.route('/strategies/<strategy_name>', methods=['GET'])
def get_strategy_status(strategy_name):
    """Get status of a specific strategy"""
    try:
        if strategy_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'Strategy manager not initialized'
            }), 500
        
        status = strategy_manager.container_manager.get_strategy_status(strategy_name)
        
        if status is None:
            return jsonify({
                'status': 'error',
                'message': f'Strategy {strategy_name} not found'
            }), 404
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting strategy status: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@algo_bp.route('/strategies/<strategy_name>/logs', methods=['GET'])
def get_strategy_logs(strategy_name):
    """Get logs for a specific strategy"""
    try:
        if strategy_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'Strategy manager not initialized'
            }), 500
        
        tail = request.args.get('tail', 100, type=int)
        logs = strategy_manager.get_strategy_logs(strategy_name, tail)
        
        return jsonify({
            'strategy_name': strategy_name,
            'logs': logs,
            'count': len(logs)
        })
        
    except Exception as e:
        logger.error(f"Error getting strategy logs: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@algo_bp.route('/strategies/<strategy_name>/restart', methods=['POST'])
def restart_strategy(strategy_name):
    """Restart a specific strategy"""
    try:
        if strategy_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'Strategy manager not initialized'
            }), 500
        
        success = strategy_manager.restart_strategy(strategy_name)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Strategy {strategy_name} restarted successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to restart strategy {strategy_name}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error restarting strategy: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@algo_bp.route('/strategies/<strategy_name>/stop', methods=['POST'])
def stop_strategy(strategy_name):
    """Stop a specific strategy"""
    try:
        if strategy_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'Strategy manager not initialized'
            }), 500
        
        success = strategy_manager.stop_strategy(strategy_name)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Strategy {strategy_name} stopped successfully'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Failed to stop strategy {strategy_name}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error stopping strategy: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@algo_bp.route('/streams', methods=['GET'])
def get_streams_info():
    """Get information about Redis Streams"""
    try:
        # Get all stream keys
        stream_keys = []
        for key in streams_manager.redis_client.scan_iter(match="market_data:*"):
            stream_info = streams_manager.get_stream_info(key)
            stream_keys.append({
                'key': key,
                'info': stream_info
            })
        
        return jsonify({
            'streams': stream_keys,
            'total_streams': len(stream_keys)
        })
        
    except Exception as e:
        logger.error(f"Error getting streams info: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@algo_bp.route('/streams/<stream_key>/trim', methods=['POST'])
def trim_stream(stream_key):
    """Trim a Redis stream to keep only recent messages"""
    try:
        data = request.get_json() or {}
        max_len = data.get('max_len', 1000)
        
        removed = streams_manager.trim_stream(stream_key, max_len)
        
        return jsonify({
            'status': 'success',
            'message': f'Trimmed stream {stream_key}',
            'removed_messages': removed
        })
        
    except Exception as e:
        logger.error(f"Error trimming stream: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@algo_bp.route('/performance', methods=['GET'])
def get_performance_metrics():
    """Get performance metrics for all strategies"""
    try:
        if strategy_manager is None:
            return jsonify({
                'status': 'error',
                'message': 'Strategy manager not initialized'
            }), 500
        
        metrics = strategy_manager.container_manager.get_performance_metrics()
        return jsonify(metrics)
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@algo_bp.route('/templates', methods=['GET'])
def get_strategy_templates():
    """Get available strategy templates"""
    templates = {
        'moving_average': {
            'name': 'Moving Average Crossover',
            'description': 'Simple moving average crossover strategy',
            'parameters': {
                'fast_period': {'type': 'int', 'default': 10, 'min': 5, 'max': 50},
                'slow_period': {'type': 'int', 'default': 20, 'min': 10, 'max': 100},
                'min_trend_strength': {'type': 'float', 'default': 0.1, 'min': 0.01, 'max': 1.0},
                'volume_threshold': {'type': 'int', 'default': 1000, 'min': 100, 'max': 10000}
            },
            'risk_management': {
                'stop_loss_pct': {'type': 'float', 'default': 0.02, 'min': 0.01, 'max': 0.1},
                'take_profit_pct': {'type': 'float', 'default': 0.05, 'min': 0.02, 'max': 0.2}
            }
        },
        'rsi': {
            'name': 'RSI Strategy',
            'description': 'Relative Strength Index based strategy',
            'parameters': {
                'rsi_period': {'type': 'int', 'default': 14, 'min': 7, 'max': 30},
                'oversold_level': {'type': 'int', 'default': 30, 'min': 20, 'max': 40},
                'overbought_level': {'type': 'int', 'default': 70, 'min': 60, 'max': 80},
                'momentum_threshold': {'type': 'float', 'default': 0.5, 'min': 0.1, 'max': 2.0}
            },
            'risk_management': {
                'stop_loss_pct': {'type': 'float', 'default': 0.02, 'min': 0.01, 'max': 0.1},
                'take_profit_pct': {'type': 'float', 'default': 0.05, 'min': 0.02, 'max': 0.2}
            }
        },
        'macd': {
            'name': 'MACD Strategy',
            'description': 'Moving Average Convergence Divergence strategy',
            'parameters': {
                'fast_period': {'type': 'int', 'default': 12, 'min': 5, 'max': 30},
                'slow_period': {'type': 'int', 'default': 26, 'min': 15, 'max': 50},
                'signal_period': {'type': 'int', 'default': 9, 'min': 5, 'max': 20},
                'histogram_threshold': {'type': 'float', 'default': 0.001, 'min': 0.0001, 'max': 0.01}
            },
            'risk_management': {
                'stop_loss_pct': {'type': 'float', 'default': 0.02, 'min': 0.01, 'max': 0.1},
                'take_profit_pct': {'type': 'float', 'default': 0.05, 'min': 0.02, 'max': 0.2}
            }
        },
        'bollinger_bands': {
            'name': 'Bollinger Bands Strategy',
            'description': 'Bollinger Bands based strategy with squeeze detection',
            'parameters': {
                'period': {'type': 'int', 'default': 20, 'min': 10, 'max': 50},
                'std_dev': {'type': 'float', 'default': 2.0, 'min': 1.0, 'max': 3.0},
                'squeeze_threshold': {'type': 'float', 'default': 0.1, 'min': 0.05, 'max': 0.3},
                'volatility_threshold': {'type': 'float', 'default': 0.02, 'min': 0.01, 'max': 0.1}
            },
            'risk_management': {
                'stop_loss_pct': {'type': 'float', 'default': 0.02, 'min': 0.01, 'max': 0.1},
                'take_profit_pct': {'type': 'float', 'default': 0.05, 'min': 0.02, 'max': 0.2}
            }
        }
    }
    
    return jsonify(templates)

# Initialize strategy manager when blueprint is registered
def init_algo_routes(app):
    """Initialize algorithmic trading routes"""
    app.register_blueprint(algo_bp)
    init_strategy_manager() 