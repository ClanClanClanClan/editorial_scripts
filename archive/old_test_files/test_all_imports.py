#!/usr/bin/env python3
"""
Test all imports to ensure dependencies are properly installed
"""

import sys
import os

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import traceback
from typing import List, Tuple

def test_import(module_path: str, description: str) -> Tuple[bool, str]:
    """Test importing a module"""
    try:
        __import__(module_path)
        return True, f"✅ {description}"
    except ImportError as e:
        return False, f"❌ {description}: {str(e)}"
    except Exception as e:
        return False, f"❌ {description}: {type(e).__name__}: {str(e)}"

def main():
    print("🧪 Testing All Imports for Editorial Scripts")
    print("=" * 50)
    
    # Core Python modules
    core_modules = [
        ("fastapi", "FastAPI web framework"),
        ("pydantic", "Pydantic validation"),
        ("sqlalchemy", "SQLAlchemy ORM"),
        ("asyncpg", "AsyncPG PostgreSQL driver"),
        ("numpy", "NumPy for numerical operations"),
        ("openai", "OpenAI API client"),
        ("pytest", "Pytest testing framework"),
        ("httpx", "HTTPX HTTP client"),
        ("redis", "Redis client"),
        ("PyPDF2", "PyPDF2 for PDF processing"),
        ("playwright", "Playwright for web automation"),
        ("bs4", "BeautifulSoup for HTML parsing"),
        ("email_validator", "Email validation"),
        ("prometheus_client", "Prometheus metrics"),
    ]
    
    print("\n📦 Testing Core Dependencies:")
    failures = []
    for module, desc in core_modules:
        success, message = test_import(module, desc)
        print(message)
        if not success:
            failures.append((module, message))
    
    # Test application modules
    app_modules = [
        ("src.api.main", "Main API application"),
        ("src.infrastructure.config", "Configuration"),
        ("src.infrastructure.database.engine", "Database engine"),
        ("src.infrastructure.repositories.referee_repository_fixed", "Referee repository"),
        ("src.ai.services", "AI services"),
        ("src.ai.models.manuscript_analysis", "AI models"),
        ("src.api.routers.ai_analysis", "AI API endpoints"),
        ("analytics.models.referee_metrics", "Analytics models"),
    ]
    
    print("\n🏗️ Testing Application Modules:")
    for module, desc in app_modules:
        success, message = test_import(module, desc)
        print(message)
        if not success:
            failures.append((module, message))
    
    # Summary
    print("\n" + "=" * 50)
    if not failures:
        print("✅ All imports successful! Environment is properly configured.")
        return 0
    else:
        print(f"❌ {len(failures)} import failures detected:\n")
        for module, message in failures:
            print(f"  {message}")
        print("\n💡 Run 'pip install -r requirements.txt' to install missing dependencies")
        return 1

if __name__ == "__main__":
    sys.exit(main())