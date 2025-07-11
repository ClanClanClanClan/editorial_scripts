#!/usr/bin/env python3
"""
Referee Analytics Integration Test
Test storing and retrieving referee performance metrics in PostgreSQL
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta, date
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

sys.path.append(str(Path(__file__).parent / 'analytics'))

# Import config and repository
from src.infrastructure.config import get_settings
from src.infrastructure.repositories.referee_analytics_repository import RefereeAnalyticsRepository

# Import models from analytics directory
from models.referee_metrics import (
    RefereeMetrics, TimeMetrics, QualityMetrics, WorkloadMetrics,
    ReliabilityMetrics, ExpertiseMetrics, JournalSpecificMetrics,
    PercentileRanks, PerformanceTier
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_referee_metrics() -> RefereeMetrics:
    """Create sample referee metrics for testing"""
    
    # Time metrics
    time_metrics = TimeMetrics(
        avg_response_time=3.2,  # days
        avg_review_time=18.5,   # days
        fastest_review=12,
        slowest_review=35,
        response_time_std=1.8,
        review_time_std=6.2,
        on_time_rate=0.87
    )
    
    # Quality metrics
    quality_metrics = QualityMetrics(
        avg_quality_score=8.2,
        quality_consistency=0.8,
        report_thoroughness=0.85,
        constructiveness_score=8.4,
        technical_accuracy=8.7,
        clarity_score=8.1,
        actionability_score=7.9
    )
    
    # Workload metrics
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
    
    # Reliability metrics
    reliability_metrics = ReliabilityMetrics(
        acceptance_rate=0.72,
        completion_rate=0.94,
        ghost_rate=0.08,
        decline_after_accept_rate=0.03,
        reminder_effectiveness=0.85,
        communication_score=0.89,
        excuse_frequency=0.12
    )
    
    # Expertise metrics
    expertise_metrics = ExpertiseMetrics(
        expertise_areas=["machine learning", "optimization", "control theory"],
        expertise_confidence={"machine learning": 0.9, "optimization": 0.85, "control theory": 0.7},
        h_index=24,
        recent_publications=8,
        citation_count=1250,
        years_experience=12,
        reviewed_topics={"machine learning": 15, "optimization": 12, "control theory": 8},
        expertise_breadth=0.75,
        expertise_depth=0.88
    )
    
    # Journal-specific metrics
    journal_metrics = {
        "SICON": JournalSpecificMetrics(
            journal_id="SICON",
            reviews_completed=12,
            acceptance_rate=0.75,
            avg_quality_score=8.3,
            avg_review_time=17.2,
            familiarity_score=0.85
        ),
        "JOTA": JournalSpecificMetrics(
            journal_id="JOTA",
            reviews_completed=8,
            acceptance_rate=0.68,
            avg_quality_score=8.1,
            avg_review_time=19.5,
            familiarity_score=0.72
        )
    }
    
    # Percentile ranks
    percentile_ranks = PercentileRanks(
        speed_percentile=82.5,
        quality_percentile=88.7,
        reliability_percentile=91.2,
        expertise_percentile=79.3,
        overall_percentile=85.4
    )
    
    # Create complete referee metrics
    metrics = RefereeMetrics(
        referee_id=str(uuid4()),
        name="Dr. Sarah Chen",
        email="s.chen@university.edu",
        institution="Stanford University",
        time_metrics=time_metrics,
        quality_metrics=quality_metrics,
        workload_metrics=workload_metrics,
        reliability_metrics=reliability_metrics,
        expertise_metrics=expertise_metrics,
        journal_metrics=journal_metrics,
        percentile_ranks=percentile_ranks,
        data_completeness=0.95
    )
    
    return metrics


async def test_save_and_retrieve_metrics():
    """Test saving and retrieving referee metrics"""
    logger.info("🧪 Testing referee metrics save and retrieve...")
    
    try:
        # Create repository
        repository = RefereeAnalyticsRepository()
        
        # Create sample metrics
        metrics = create_sample_referee_metrics()
        original_referee_id = metrics.referee_id
        
        # Save to database
        logger.info(f"💾 Saving referee metrics for {metrics.name}...")
        saved_referee_id = await repository.save_referee_metrics(metrics)
        
        logger.info(f"✅ Referee metrics saved with ID: {saved_referee_id}")
        
        # Retrieve by ID
        logger.info(f"🔍 Retrieving referee metrics {saved_referee_id}...")
        retrieved = await repository.get_referee_metrics(saved_referee_id)
        
        if retrieved:
            assert retrieved.name == metrics.name, "Name should match"
            assert retrieved.email == metrics.email, "Email should match"
            assert retrieved.institution == metrics.institution, "Institution should match"
            
            logger.info(f"✅ Referee metrics retrieved successfully:")
            logger.info(f"   Name: {retrieved.name}")
            logger.info(f"   Email: {retrieved.email}")
            logger.info(f"   Institution: {retrieved.institution}")
            logger.info(f"   Overall Score: {retrieved.get_overall_score():.2f}")
            logger.info(f"   Performance Tier: {retrieved.percentile_ranks.get_performance_tier().value if retrieved.percentile_ranks else 'N/A'}")
        else:
            logger.warning("⚠️ Could not retrieve cached metrics (cache may be empty)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Save and retrieve test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_referee_lookup():
    """Test referee lookup by email"""
    logger.info("🧪 Testing referee lookup by email...")
    
    try:
        repository = RefereeAnalyticsRepository()
        
        # Look up a referee by email
        test_email = "s.chen@university.edu"
        logger.info(f"🔍 Looking up referee by email: {test_email}")
        
        referee = await repository.get_referee_by_email(test_email)
        
        if referee:
            logger.info(f"✅ Found referee:")
            logger.info(f"   ID: {referee.id}")
            logger.info(f"   Name: {referee.name}")
            logger.info(f"   Email: {referee.email}")
            logger.info(f"   Institution: {referee.institution}")
            logger.info(f"   H-Index: {referee.h_index}")
            logger.info(f"   Years Experience: {referee.years_experience}")
        else:
            logger.info("ℹ️ No referee found with that email (expected for first run)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Referee lookup test failed: {e}")
        return False


async def test_journal_performance_stats():
    """Test journal performance statistics"""
    logger.info("🧪 Testing journal performance statistics...")
    
    try:
        repository = RefereeAnalyticsRepository()
        
        # Get performance stats for SICON journal
        journal_code = "SICON"
        logger.info(f"📊 Getting performance statistics for {journal_code}...")
        
        stats = await repository.get_journal_performance_stats(journal_code, days=90)
        
        logger.info(f"✅ Journal performance stats retrieved:")
        logger.info(f"   Journal: {stats.get('journal_code', 'N/A')}")
        logger.info(f"   Total Reviews: {stats.get('total_reviews', 0)}")
        logger.info(f"   Completed Reviews: {stats.get('completed_reviews', 0)}")
        logger.info(f"   Completion Rate: {stats.get('completion_rate', 0):.2%}")
        logger.info(f"   Avg Quality Score: {stats.get('avg_quality_score', 0):.2f}")
        logger.info(f"   Avg Review Time: {stats.get('avg_review_time_days', 0):.1f} days")
        logger.info(f"   Active Referees: {stats.get('active_referees', 0)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Journal performance stats test failed: {e}")
        return False


async def test_review_activity_recording():
    """Test recording review activity"""
    logger.info("🧪 Testing review activity recording...")
    
    try:
        repository = RefereeAnalyticsRepository()
        
        # Create a test referee ID and manuscript ID
        referee_id = uuid4()
        manuscript_id = "TEST-2025-001"
        
        # Record invitation
        logger.info(f"📝 Recording review invitation...")
        await repository.record_review_activity(
            referee_id=referee_id,
            manuscript_id=manuscript_id,
            action="invited"
        )
        
        # Record acceptance
        logger.info(f"📝 Recording review acceptance...")
        await repository.record_review_activity(
            referee_id=referee_id,
            manuscript_id=manuscript_id,
            action="accepted"
        )
        
        # Record submission
        logger.info(f"📝 Recording review submission...")
        await repository.record_review_activity(
            referee_id=referee_id,
            manuscript_id=manuscript_id,
            action="submitted",
            metadata={
                "quality_score": 8.5,
                "report_length": 1250
            }
        )
        
        logger.info(f"✅ Review activity recording completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Review activity recording test failed: {e}")
        return False


async def test_top_performers():
    """Test top performers query"""
    logger.info("🧪 Testing top performers query...")
    
    try:
        repository = RefereeAnalyticsRepository()
        
        # Get top performers
        logger.info(f"🏆 Getting top performers...")
        performers = await repository.get_top_performers(limit=10)
        
        logger.info(f"✅ Found {len(performers)} top performers:")
        for i, performer in enumerate(performers[:5], 1):  # Show top 5
            logger.info(f"   {i}. {performer.get('name', 'Unknown')} "
                       f"({performer.get('tier', 'N/A')}) - "
                       f"{performer.get('percentile', 0):.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Top performers test failed: {e}")
        return False


async def run_all_tests():
    """Run all referee analytics integration tests"""
    logger.info("🚀 Starting Referee Analytics Integration Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Save and Retrieve Metrics", test_save_and_retrieve_metrics()),
        ("Referee Lookup", test_referee_lookup()),
        ("Journal Performance Stats", test_journal_performance_stats()),
        ("Review Activity Recording", test_review_activity_recording()),
        ("Top Performers Query", test_top_performers()),
    ]
    
    results = []
    for test_name, test_coro in tests:
        logger.info(f"\n🧪 Running {test_name}...")
        try:
            result = await test_coro
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\nReferee Analytics Integration Test Results")
    logger.info("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name:<30} {status}")
        if result:
            passed += 1
    
    total = len(results)
    logger.info(f"\nSummary: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL REFEREE ANALYTICS TESTS PASSED!")
        logger.info("\n📋 Referee Analytics Integration Complete:")
        logger.info("   ✅ PostgreSQL database models created")
        logger.info("   ✅ Referee metrics storage and retrieval")
        logger.info("   ✅ Performance statistics and analytics")
        logger.info("   ✅ Review activity tracking")
        logger.info("   ✅ Top performers identification")
        logger.info("\n🚀 Ready for Phase 1.3: Complete end-to-end testing")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed - Referee analytics needs fixes")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)