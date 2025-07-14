#!/usr/bin/env python3
"""
Test basic imports for referee analytics
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.append(str(Path(__file__).parent / 'analytics'))

print("🧪 Testing basic imports...")

try:
    from models.referee_metrics import RefereeMetrics, TimeMetrics
    print("✅ referee_metrics imported")
except Exception as e:
    print(f"❌ referee_metrics import failed: {e}")

try:
    from src.infrastructure.database.referee_models import RefereeAnalyticsModel
    print("✅ referee_models imported")
except Exception as e:
    print(f"❌ referee_models import failed: {e}")

try:
    from src.infrastructure.repositories.referee_analytics_repository import RefereeAnalyticsRepository
    print("✅ referee_analytics_repository imported")
except Exception as e:
    print(f"❌ referee_analytics_repository import failed: {e}")

try:
    from src.infrastructure.config import get_settings
    settings = get_settings()
    print(f"✅ config imported - DB: {settings.db_name}")
except Exception as e:
    print(f"❌ config import failed: {e}")

print("🎯 Import test complete!")