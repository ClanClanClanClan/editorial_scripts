#!/bin/bash
# Script to run the API server

echo "🚀 Starting Editorial Scripts API Server"
echo "======================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
echo "📦 Installing dependencies..."
pip install -q fastapi uvicorn httpx pytest pytest-asyncio \
    sqlalchemy asyncpg psycopg2-binary alembic \
    pydantic email-validator python-multipart \
    prometheus-fastapi-instrumentator

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export DATABASE_URL="postgresql://dylanpossamai:@localhost:5432/editorial_scripts"
export ENVIRONMENT="development"
export DEBUG="true"

# Run the server
echo ""
echo "🌐 Starting server on http://localhost:8000"
echo "📚 API docs available at http://localhost:8000/docs"
echo "📊 Metrics available at http://localhost:8000/metrics"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000