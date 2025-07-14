#!/usr/bin/env /usr/bin/python3
"""
Simple verification test - create one referee and verify all operations work
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.append(str(Path(__file__).parent / 'analytics'))

print("🔍 SIMPLE VERIFICATION TEST")
print("=" * 50)


async def test():
    try:
        # Import
        from src.infrastructure.repositories.referee_repository_fixed import RefereeRepositoryFixed
        from models.referee_metrics import (
            RefereeMetrics, TimeMetrics, QualityMetrics, WorkloadMetrics,
            ReliabilityMetrics, ExpertiseMetrics
        )
        
        repo = RefereeRepositoryFixed()
        print("✅ Imports successful")
        
        # Create metrics
        metrics = RefereeMetrics(
            referee_id=str(uuid4()),
            name="Simple Test",
            email=f"simple_{datetime.now().timestamp()}@test.com",
            institution="Test University",
            time_metrics=TimeMetrics(3, 21, 10, 40, 1, 5, 0.8),
            quality_metrics=QualityMetrics(7.5, 0.8, 0.85, 8, 8.2, 7.8, 7.6),
            workload_metrics=WorkloadMetrics(2, 4, 12, 48, 4, 5, 0.8, 0.2),
            reliability_metrics=ReliabilityMetrics(0.75, 0.92, 0.08, 0.03, 0.85, 0.88, 0.1),
            expertise_metrics=ExpertiseMetrics(
                expertise_areas=["machine learning", "AI"],
                h_index=25,
                years_experience=10
            )
        )
        
        # Save
        saved_id = await repo.save_referee_metrics(metrics)
        print(f"✅ Saved with ID: {saved_id}")
        
        # Retrieve
        retrieved = await repo.get_referee_metrics(saved_id)
        if retrieved and retrieved.name == "Simple Test":
            print("✅ Retrieved successfully")
            print(f"   Overall score: {retrieved.get_overall_score():.2f}")
        else:
            print("❌ Retrieval failed")
            return False
        
        # Stats
        stats = await repo.get_performance_stats()
        print(f"✅ Stats: {stats.get('total_referees')} referees")
        
        # Top performers
        top = await repo.get_top_performers(limit=5)
        print(f"✅ Top performers: {len(top)} found")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test())
    print("\n" + "=" * 50)
    if success:
        print("✅ VERIFICATION SUCCESSFUL - System is working")
    else:
        print("❌ VERIFICATION FAILED - System has issues")
    sys.exit(0 if success else 1)