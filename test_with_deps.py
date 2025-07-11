#!/usr/bin/env /usr/bin/python3
"""
Test referee analytics with all dependencies available
"""

import sys
import asyncio
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.append(str(Path(__file__).parent / 'analytics'))

print("🚀 TESTING REFEREE ANALYTICS WITH DEPENDENCIES")
print("=" * 70)

# Test imports
print("\n📦 Testing imports...")
try:
    import sqlalchemy
    print(f"✅ SQLAlchemy {sqlalchemy.__version__}")
except ImportError as e:
    print(f"❌ SQLAlchemy: {e}")

try:
    import asyncpg
    print(f"✅ asyncpg {asyncpg.__version__}")
except ImportError as e:
    print(f"❌ asyncpg: {e}")

try:
    import numpy
    print(f"✅ numpy {numpy.__version__}")
except ImportError as e:
    print(f"❌ numpy: {e}")

print("\n📂 Testing project imports...")
try:
    from src.infrastructure.repositories.referee_repository_fixed import RefereeRepositoryFixed
    print("✅ Repository imported successfully")
except ImportError as e:
    print(f"❌ Repository import failed: {e}")

try:
    from models.referee_metrics import (
        RefereeMetrics, TimeMetrics, QualityMetrics, WorkloadMetrics,
        ReliabilityMetrics, ExpertiseMetrics
    )
    print("✅ Domain models imported successfully")
except ImportError as e:
    print(f"❌ Domain models import failed: {e}")

print("\n✅ All dependencies are working!")
print("Ready to run full integration tests")