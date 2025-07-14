#!/bin/bash

# Clean Environment Script - Removes all virtual environments and caches

echo "🧹 Cleaning Editorial Scripts Environment"
echo "========================================"

# Remove virtual environments
echo "🗑️  Removing virtual environments..."
rm -rf venv .venv env .env_backup venv_new .venv_new 2>/dev/null || true

# Remove Python cache
echo "🗑️  Removing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.pyd" -delete 2>/dev/null || true
find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Remove pytest cache
echo "🗑️  Removing pytest cache..."
rm -rf .pytest_cache 2>/dev/null || true
rm -rf .coverage 2>/dev/null || true
rm -rf htmlcov 2>/dev/null || true

# Remove build artifacts
echo "🗑️  Removing build artifacts..."
rm -rf build dist *.egg-info 2>/dev/null || true

# Remove mypy cache
echo "🗑️  Removing mypy cache..."
rm -rf .mypy_cache 2>/dev/null || true

# Remove IDE-specific files
echo "🗑️  Removing IDE files..."
rm -rf .idea .vscode 2>/dev/null || true

# Remove temporary files
echo "🗑️  Removing temporary files..."
find . -type f -name ".DS_Store" -delete 2>/dev/null || true
find . -type f -name "*.tmp" -delete 2>/dev/null || true
find . -type f -name "*.log" -delete 2>/dev/null || true

echo ""
echo "✅ Environment cleaned!"
echo ""
echo "📌 To set up a fresh environment, run:"
echo "   ./setup_environment.sh"