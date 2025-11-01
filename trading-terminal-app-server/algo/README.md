# Algorithmic Trading System

This directory contains a comprehensive algorithmic trading system built with Redis Streams and Docker containers. The system provides real-time market data distribution, modular trading strategies, and containerized execution for scalability and reliability.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Market Data   │    │   Redis Streams │    │  Strategy       │
│   Feeders       │───▶│   (Real-time    │───▶│  Containers     │
│                 │    │   distribution) │    │  (Docker)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Strategy      │
                       │   Manager       │
                       │  (Orchestration)│
                       └─────────────────┘
```

## Key Components

### 1. Redis Streams (`redis_streams.py`)
- **Purpose**: Real-time market data distribution
- **Features**:
  - Consumer groups for reliable message delivery
  - Fault tolerance with message acknowledgment
  - Stream trimming for memory management
  - Divergence detection for pending messages

### 2. Strategy Base Class (`strategies/base_strategy.py`)
- **Purpose**: Foundation for all trading strategies
- **Features**:
  - Redis Streams integration
  - Signal generation and management
  - Position tracking and PnL calculation
  - Risk management utilities
  - Performance metrics

### 3. Trading Strategies
- **Moving Average Crossover** (`strategies/moving_average_strategy.py`)
- **RSI Strategy** (`strategies/rsi_strategy.py`)
- **MACD Strategy** (`strategies/macd_strategy.py`)
- **Bollinger Bands Strategy** (`strategies/bollinger_bands_strategy.py`)

### 4. Docker Container Management
- **Strategy Container** (`containers/strategy_container.py`)
- **Container Manager** (`containers/container_manager.py`)
- **Docker Utilities** (`containers/docker_utils.py`)

### 5. Strategy Runner (`strategy_runner.py`)
- **Purpose**: Main entry point for Docker containers
- **Features**:
  - Environment-based configuration
  - Graceful shutdown handling
  - Health monitoring
  - Performance metrics

### 6. Strategy Manager (`strategy_manager.py`)
- **Purpose**: Orchestration service for all strategy containers
- **Features**:
  - Container lifecycle management
  - Health monitoring and auto-recovery
  - Performance metrics aggregation
  - API endpoints for management

## Quick Start

### 1. Start the System
```bash
# Start all services including strategy containers
docker-compose up -d

# Check status
docker-compose ps
```

### 2. Deploy a Strategy
```bash
# Deploy a moving average strategy
curl -X POST http://localhost:8000/api/algo/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "ma_btc_strategy",
    "strategy_type": "moving_average",
    "symbols": ["BTCUSDT"],
    "exchange": "binance",
    "parameters": {
      "fast_period": 10,
      "slow_period": 20,
      "min_trend_strength": 0.1
    },
    "risk_management": {
      "stop_loss_pct": 0.02,
      "take_profit_pct": 0.05
    }
  }'
```

### 3. Monitor Strategies
```bash
# Get all strategies status
curl http://localhost:8000/api/algo/strategies

# Get specific strategy logs
curl http://localhost:8000/api/algo/strategies/ma_btc_strategy/logs

# Get performance metrics
curl http://localhost:8000/api/algo/performance
```

## API Endpoints

### Strategy Management
- `GET /api/algo/health` - Health check
- `GET /api/algo/strategies` - Get all strategies
- `POST /api/algo/strategies` - Deploy new strategy
- `GET /api/algo/strategies/<name>` - Get strategy status
- `POST /api/algo/strategies/<name>/restart` - Restart strategy
- `POST /api/algo/strategies/<name>/stop` - Stop strategy
- `GET /api/algo/strategies/<name>/logs` - Get strategy logs

### Redis Streams Management
- `GET /api/algo/streams` - Get streams information
- `POST /api/algo/streams/<key>/trim` - Trim stream

### Performance & Templates
- `GET /api/algo/performance` - Get performance metrics
- `GET /api/algo/templates` - Get strategy templates

## Strategy Types

### 1. Moving Average Crossover
- **Parameters**: `fast_period`, `slow_period`, `min_trend_strength`, `volume_threshold`
- **Signals**: BUY when fast MA crosses above slow MA, SELL when crosses below

### 2. RSI Strategy
- **Parameters**: `rsi_period`, `oversold_level`, `overbought_level`, `momentum_threshold`
- **Signals**: BUY when RSI crosses above oversold level, SELL when crosses below overbought level

### 3. MACD Strategy
- **Parameters**: `fast_period`, `slow_period`, `signal_period`, `histogram_threshold`
- **Signals**: BUY when MACD line crosses above signal line, SELL when crosses below

### 4. Bollinger Bands Strategy
- **Parameters**: `period`, `std_dev`, `squeeze_threshold`, `volatility_threshold`
- **Signals**: BUY when price touches lower band, SELL when touches upper band

## Configuration

### Environment Variables
```bash
# Strategy Manager
MAX_CONTAINERS=10
MAX_MEMORY_PER_CONTAINER=512m
MAX_CPU_PER_CONTAINER=0.5
HEALTH_CHECK_INTERVAL=30
AUTO_RESTART_FAILED=true

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Strategy Container
STRATEGY_NAME=my_strategy
STRATEGY_TYPE=moving_average
SYMBOLS=["BTCUSDT", "ETHUSDT"]
EXCHANGE=binance
PARAMETERS={"fast_period": 10, "slow_period": 20}
RISK_MANAGEMENT={"stop_loss_pct": 0.02, "take_profit_pct": 0.05}
```

## Docker Compose Services

### Core Services
- **trading-api**: Main API server
- **redis**: Redis database for streams and caching
- **strategy-manager**: Orchestration service

### Strategy Containers
- **moving-average-strategy**: Example MA crossover strategy
- **rsi-strategy**: Example RSI strategy
- **macd-strategy**: Example MACD strategy
- **bollinger-bands-strategy**: Example Bollinger Bands strategy

## Monitoring and Logs

### Container Logs
```bash
# View strategy container logs
docker logs ma-strategy-1

# View manager logs
docker logs strategy-manager
```

### Performance Monitoring
- Memory usage per container
- CPU usage per container
- Network I/O statistics
- Strategy performance metrics

### Health Checks
- Container health status
- Redis connection status
- Strategy execution status
- Auto-restart on failures

## Development

### Adding New Strategies
1. Create new strategy class inheriting from `BaseStrategy`
2. Implement `_generate_signals()` method
3. Add strategy type to `strategy_runner.py`
4. Update API templates in `algo_routes.py`

### Testing
```bash
# Run tests
pytest tests/

# Test specific strategy
python -m algo.strategy_runner
```

### Building Images
```bash
# Build strategy image
docker build -t trading-strategy .

# Build manager image
docker build -t trading-strategy-manager .
```

## Security Considerations

- Non-root user in containers
- Resource limits (CPU, memory)
- Network isolation
- Secure Redis configuration
- Environment variable validation

## Scaling

### Horizontal Scaling
- Deploy multiple strategy containers
- Load balancing across containers
- Resource allocation per strategy

### Vertical Scaling
- Increase container resources
- Optimize strategy parameters
- Enhance monitoring and alerting

## Troubleshooting

### Common Issues
1. **Redis Connection Failed**: Check Redis service status
2. **Container Won't Start**: Check resource limits and logs
3. **Strategy Not Generating Signals**: Verify market data availability
4. **High Memory Usage**: Monitor and adjust container limits

### Debug Commands
```bash
# Check container status
docker ps -a

# View container stats
docker stats

# Check Redis streams
redis-cli XINFO STREAM market_data:binance:BTCUSDT:tick

# Monitor logs in real-time
docker logs -f strategy-manager
```

## Contributing

1. Follow the existing code structure
2. Add comprehensive tests
3. Update documentation
4. Follow Docker best practices
5. Implement proper error handling

## License

This algorithmic trading system is part of the Trading Terminal project. 