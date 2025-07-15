#!/bin/bash

# Editorial Scripts - Clean Environment Setup Script
# This script creates a clean virtual environment with all dependencies

set -e  # Exit on error

echo "🧹 Editorial Scripts - Clean Environment Setup"
echo "============================================"

# Check Python version
echo "📍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo "❌ Error: Python 3.11+ is required. Current version: $python_version"
    exit 1
fi
echo "✅ Python version: $python_version"

# Clean up existing virtual environments
echo ""
echo "🧹 Cleaning up existing virtual environments..."
rm -rf venv .venv env .env venv_new .venv_new 2>/dev/null || true
echo "✅ Cleaned up old environments"

# Create new virtual environment
echo ""
echo "🔧 Creating fresh virtual environment..."
python3 -m venv venv
echo "✅ Virtual environment created"

# Activate virtual environment
echo ""
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "📦 Upgrading pip..."
pip install --upgrade pip setuptools wheel
echo "✅ Pip upgraded"

# Install dependencies
echo ""
echo "📚 Installing dependencies..."
pip install -r requirements.txt
echo "✅ All dependencies installed"

# Install playwright browsers (if needed for web scraping)
echo ""
echo "🌐 Installing Playwright browsers..."
playwright install chromium || echo "⚠️  Playwright browsers installation skipped"

# Create necessary directories
echo ""
echo "📁 Creating necessary directories..."
mkdir -p data logs cache temp extractions ai_analysis_cache
echo "✅ Directories created"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file from example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ .env file created (please update with your values)"
    else
        echo "# Editorial Scripts Environment Variables" > .env
        echo "ENVIRONMENT=development" >> .env
        echo "DEBUG=true" >> .env
        echo "DATABASE_URL=postgresql+asyncpg://user:password@localhost/editorial_scripts" >> .env
        echo "OPENAI_API_KEY=your-openai-api-key-here" >> .env
        echo "SECRET_KEY=your-secret-key-here" >> .env
        echo "✅ Basic .env file created (please update with your values)"
    fi
fi

# Run basic import test
echo ""
echo "🧪 Testing imports..."
python3 -c "
import sys
print(f'Python: {sys.version}')
print('Testing core imports...')
import fastapi
print('✓ FastAPI')
import sqlalchemy
print('✓ SQLAlchemy')
import pydantic
print('✓ Pydantic')
import numpy
print('✓ NumPy')
import openai
print('✓ OpenAI')
import pytest
print('✓ Pytest')
print('All core imports successful!')
" || (echo "❌ Import test failed" && exit 1)

echo ""
echo "✅ All imports successful!"

# Create activation reminder
echo ""
echo "📌 Setup complete! To activate the environment, run:"
echo "   source venv/bin/activate"
echo ""
echo "🚀 You can now run the application with:"
echo "   uvicorn src.api.main:app --reload"
echo ""
echo "🧪 To run tests:"
echo "   pytest tests/"
echo ""

# Save environment info
echo "📊 Environment Summary" > environment_info.txt
echo "=====================" >> environment_info.txt
echo "Python Version: $python_version" >> environment_info.txt
echo "Virtual Env: venv" >> environment_info.txt
echo "Setup Date: $(date)" >> environment_info.txt
echo "" >> environment_info.txt
echo "Installed Packages:" >> environment_info.txt
pip list >> environment_info.txt

echo "✅ Environment setup complete!"