#!/usr/bin/env python3
"""
Test referee analytics repository operations
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.append(str(Path(__file__).parent / 'analytics'))

print("🧪 Testing referee analytics repository...")

async def test_repository():
    try:
        # Import models
        from models.referee_metrics import (
            RefereeMetrics, TimeMetrics, QualityMetrics, WorkloadMetrics,
            ReliabilityMetrics, ExpertiseMetrics, JournalSpecificMetrics
        )
        
        # Import repository
        from src.infrastructure.repositories.referee_analytics_repository import RefereeAnalyticsRepository
        
        print("✅ All imports successful")
        
        # Create repository
        repository = RefereeAnalyticsRepository()
        print("✅ Repository created")
        
        # Create sample metrics
        time_metrics = TimeMetrics(
            avg_response_time=3.2,
            avg_review_time=18.5,
            fastest_review=12,
            slowest_review=35,
            response_time_std=1.8,
            review_time_std=6.2,
            on_time_rate=0.87
        )
        
        quality_metrics = QualityMetrics(
            avg_quality_score=8.2,
            quality_consistency=0.8,
            report_thoroughness=0.85,
            constructiveness_score=8.4,
            technical_accuracy=8.7,
            clarity_score=8.1,
            actionability_score=7.9
        )
        
        workload_metrics = WorkloadMetrics(
            current_reviews=2,
            completed_reviews_30d=3,
            completed_reviews_90d=8,
            completed_reviews_365d=28,
            monthly_average=2.3,
            peak_capacity=4,
            availability_score=0.75,
            burnout_risk_score=0.25
        )
        
        reliability_metrics = ReliabilityMetrics(
            acceptance_rate=0.72,
            completion_rate=0.94,
            ghost_rate=0.08,
            decline_after_accept_rate=0.03,
            reminder_effectiveness=0.85,
            communication_score=0.89,
            excuse_frequency=0.12
        )
        
        expertise_metrics = ExpertiseMetrics(
            expertise_areas=["machine learning", "optimization"],
            expertise_confidence={"machine learning": 0.9, "optimization": 0.85},
            h_index=24,
            recent_publications=8,
            years_experience=12
        )
        
        metrics = RefereeMetrics(
            referee_id=str(uuid4()),
            name="Dr. Sarah Test",
            email="sarah.test@university.edu",
            institution="Test University",
            time_metrics=time_metrics,
            quality_metrics=quality_metrics,
            workload_metrics=workload_metrics,
            reliability_metrics=reliability_metrics,
            expertise_metrics=expertise_metrics
        )
        
        print("✅ Sample metrics created")
        
        # Test basic lookup
        print("🔍 Testing referee lookup...")
        referee = await repository.get_referee_by_email("test@university.edu")
        if referee:
            print(f"✅ Found existing referee: {referee.name}")
        else:
            print("ℹ️ No referee found (expected for new email)")
        
        # Test save metrics
        print("💾 Testing metrics save...")
        try:
            saved_id = await repository.save_referee_metrics(metrics)
            print(f"✅ Metrics saved with referee ID: {saved_id}")
        except Exception as e:
            print(f"❌ Save failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Test retrieve metrics
        print("🔍 Testing metrics retrieval...")
        try:
            retrieved = await repository.get_referee_metrics(saved_id)
            if retrieved:
                print(f"✅ Retrieved metrics for: {retrieved.name}")
                print(f"   Overall Score: {retrieved.get_overall_score():.2f}")
            else:
                print("ℹ️ No cached metrics found (cache may be empty)")
        except Exception as e:
            print(f"❌ Retrieval failed: {e}")
            import traceback
            traceback.print_exc()
        
        return True
        
    except Exception as e:
        print(f"❌ Repository test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_repository())
    print(f"🎯 Repository test: {'PASSED' if success else 'FAILED'}")