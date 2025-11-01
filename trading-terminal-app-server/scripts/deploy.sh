#!/bin/bash

# Production deployment script for Trading API
set -e

echo "🚀 Starting production deployment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "📝 Please edit .env file with your production values"
        echo "   - Set SECRET_KEY to a strong random string"
        echo "   - Configure your API keys (BINANCE_API_KEY, BINANCE_API_SECRET, etc.)"
        echo "   - Set CORS_ORIGINS to your frontend domain"
        echo "   - Configure SENTRY_DSN for error monitoring"
        exit 1
    else
        echo "❌ No .env.example file found. Please create .env file manually."
        exit 1
    fi
fi

# Load environment variables
source .env

# Validate required environment variables
required_vars=("SECRET_KEY" "REDIS_URL")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set"
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check if the API is responding
echo "🔍 Checking API health..."
for i in {1..10}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API is healthy and responding"
        break
    else
        echo "⏳ Waiting for API to be ready... (attempt $i/10)"
        sleep 10
    fi
done

# Final health check
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "🎉 Deployment successful!"
    echo "📊 API is running at: http://localhost:8000"
    echo "📚 API Documentation: http://localhost:8000/api/docs"
    echo "💚 Health Check: http://localhost:8000/health"
    echo ""
    echo "📝 Useful commands:"
    echo "   - View logs: docker-compose logs -f"
    echo "   - Stop services: docker-compose down"
    echo "   - Restart services: docker-compose restart"
    echo "   - Update and redeploy: ./scripts/deploy.sh"
else
    echo "❌ Deployment failed - API is not responding"
    echo "📋 Checking logs..."
    docker-compose logs
    exit 1
fi 