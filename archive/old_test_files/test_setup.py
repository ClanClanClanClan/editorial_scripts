#!/usr/bin/env python3
"""
Simple test to verify environment setup
"""

import sys

print("🧪 Testing Editorial Scripts Setup")
print("=" * 50)

# Test basic imports
try:
    import fastapi
    print("✅ FastAPI imported successfully")
except ImportError as e:
    print(f"❌ FastAPI import failed: {e}")

try:
    import sqlalchemy
    print("✅ SQLAlchemy imported successfully")
except ImportError as e:
    print(f"❌ SQLAlchemy import failed: {e}")

try:
    import openai
    print("✅ OpenAI imported successfully")
except ImportError as e:
    print(f"❌ OpenAI import failed: {e}")

try:
    import asyncpg
    print("✅ AsyncPG imported successfully")
except ImportError as e:
    print(f"❌ AsyncPG import failed: {e}")

# Test app structure
print("\n📁 Testing Application Structure:")
try:
    from src.infrastructure.config import settings
    print("✅ Configuration loaded successfully")
    print(f"   Environment: {settings.environment}")
except Exception as e:
    print(f"❌ Configuration failed: {e}")

try:
    from src.infrastructure.database.engine import get_engine
    print("✅ Database engine accessible")
except Exception as e:
    print(f"❌ Database engine failed: {e}")

try:
    from src.ai.models.manuscript_analysis import ManuscriptMetadata, ComprehensiveAnalysis
    print("✅ AI models imported successfully")
except Exception as e:
    print(f"❌ AI models import failed: {e}")

print("\n✨ Setup verification complete!")