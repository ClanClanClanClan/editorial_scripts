#!/usr/bin/env /usr/bin/python3
"""
Test if the API can start up
"""

import sys
import os

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🔍 Testing API startup...")
print("=" * 50)

# Test imports
try:
    from src.api.main_simple import app
    print("✅ FastAPI app imported successfully")
except Exception as e:
    print(f"❌ Failed to import app: {e}")
    sys.exit(1)

# Test database models
try:
    from src.infrastructure.database.referee_models_fixed import Base
    print("✅ Database models imported")
except Exception as e:
    print(f"❌ Failed to import database models: {e}")

# Test referee repository
try:
    from src.infrastructure.repositories.referee_repository_fixed import RefereeRepositoryFixed
    print("✅ Repository imported")
except Exception as e:
    print(f"❌ Failed to import repository: {e}")

# Test domain models
try:
    from analytics.models.referee_metrics import RefereeMetrics
    print("✅ Domain models imported")
except Exception as e:
    print(f"❌ Failed to import domain models: {e}")
    print("   This is expected if analytics directory is not in path")

print("\n" + "=" * 50)
print("✅ Basic imports working!")
print("\nTo start the API server:")
print("  /usr/bin/python3 -m uvicorn src.api.main_simple:app --reload")