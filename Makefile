# Editorial Scripts - Development Makefile

.PHONY: help clean setup install test lint format run docs

# Default target
help:
	@echo "Editorial Scripts - Development Commands"
	@echo "======================================"
	@echo "make clean      - Clean all generated files and caches"
	@echo "make setup      - Set up fresh virtual environment"
	@echo "make install    - Install all dependencies"
	@echo "make test       - Run all tests"
	@echo "make lint       - Run linting checks"
	@echo "make format     - Format code with black and isort"
	@echo "make run        - Run the API server"
	@echo "make docs       - Build documentation"
	@echo "make check      - Run all checks (lint, test, type check)"
	@echo "make migrate    - Run database migrations"

# Clean everything
clean:
	@echo "🧹 Cleaning environment..."
	@bash clean_environment.sh
	@echo "✅ Environment cleaned"

# Set up fresh environment
setup: clean
	@echo "🔧 Setting up fresh environment..."
	@bash setup_environment.sh
	@echo "✅ Setup complete"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	@pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Install development dependencies
install-dev:
	@echo "📦 Installing development dependencies..."
	@pip install -r requirements-dev.txt
	@echo "✅ Development dependencies installed"

# Run tests
test:
	@echo "🧪 Running tests..."
	@pytest tests/ -v
	@echo "✅ Tests complete"

# Run specific test file
test-file:
	@echo "🧪 Running specific test..."
	@pytest $(FILE) -v

# Run linting
lint:
	@echo "🔍 Running linting checks..."
	@flake8 src/ analytics/ --max-line-length=100
	@isort --check-only src/ analytics/
	@black --check src/ analytics/
	@echo "✅ Linting complete"

# Format code
format:
	@echo "🎨 Formatting code..."
	@isort src/ analytics/ tests/
	@black src/ analytics/ tests/
	@echo "✅ Code formatted"

# Type checking
type-check:
	@echo "🔍 Running type checks..."
	@mypy src/ analytics/
	@echo "✅ Type checking complete"

# Run all checks
check: lint type-check test
	@echo "✅ All checks passed!"

# Run the API server
run:
	@echo "🚀 Starting API server..."
	@uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Run with custom settings
run-prod:
	@echo "🚀 Starting API server (production mode)..."
	@uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Build documentation
docs:
	@echo "📚 Building documentation..."
	@mkdocs build
	@echo "✅ Documentation built in site/"

# Serve documentation
docs-serve:
	@echo "📚 Serving documentation..."
	@mkdocs serve

# Database migrations
migrate:
	@echo "🗄️ Running database migrations..."
	@alembic upgrade head
	@echo "✅ Migrations complete"

# Create new migration
migrate-create:
	@echo "🗄️ Creating new migration..."
	@alembic revision --autogenerate -m "$(MSG)"

# Test imports
test-imports:
	@echo "🧪 Testing all imports..."
	@python test_all_imports.py

# Security check
security:
	@echo "🔒 Running security checks..."
	@bandit -r src/ analytics/
	@safety check
	@echo "✅ Security checks complete"

# Clean Python cache
clean-cache:
	@echo "🗑️ Cleaning Python cache..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cache cleaned"

# Full clean and setup
refresh: clean setup install install-dev
	@echo "✅ Environment refreshed and ready!"

# Show environment info
info:
	@echo "📊 Environment Information"
	@echo "========================"
	@python --version
	@pip --version
	@echo ""
	@echo "Virtual Environment:"
	@which python
	@echo ""
	@echo "Installed Packages:"
	@pip list | head -20
	@echo "..."
	@echo "Total packages: $$(pip list | wc -l)"

# Quick test for CI/CD
ci-test:
	@pytest tests/ -v --cov=src --cov-report=term-missing

# Build for production
build:
	@echo "🏗️ Building for production..."
	@pip install --upgrade build
	@python -m build
	@echo "✅ Build complete"

# Docker commands (if using Docker)
docker-build:
	@echo "🐳 Building Docker image..."
	@docker build -t editorial-scripts:latest .

docker-run:
	@echo "🐳 Running Docker container..."
	@docker run -p 8000:8000 --env-file .env editorial-scripts:latest