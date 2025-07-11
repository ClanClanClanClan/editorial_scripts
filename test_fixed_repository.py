#!/usr/bin/env python3
"""
TEST THE ACTUALLY FIXED REPOSITORY
No more bullshit - this better work
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.append(str(Path(__file__).parent / 'analytics'))

print("🔥 TESTING THE ACTUALLY FIXED REPOSITORY")
print("=" * 60)

async def test_fixed_repository():
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Import the fixed repository
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Import fixed repository")
    try:
        from src.infrastructure.repositories.referee_repository_fixed import RefereeRepositoryFixed
        from models.referee_metrics import (
            RefereeMetrics, TimeMetrics, QualityMetrics, WorkloadMetrics,
            ReliabilityMetrics, ExpertiseMetrics
        )
        
        repo = RefereeRepositoryFixed()
        print("✅ Fixed repository imported successfully")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Create domain model
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Create complete domain model")
    try:
        time_metrics = TimeMetrics(
            avg_response_time=2.8,
            avg_review_time=17.5,
            fastest_review=12,
            slowest_review=28,
            response_time_std=1.5,
            review_time_std=4.2,
            on_time_rate=0.89
        )
        
        quality_metrics = QualityMetrics(
            avg_quality_score=8.4,
            quality_consistency=0.85,
            report_thoroughness=0.9,
            constructiveness_score=8.6,
            technical_accuracy=8.8,
            clarity_score=8.2,
            actionability_score=8.1
        )
        
        workload_metrics = WorkloadMetrics(
            current_reviews=2,
            completed_reviews_30d=4,
            completed_reviews_90d=11,
            completed_reviews_365d=42,
            monthly_average=3.5,
            peak_capacity=5,
            availability_score=0.8,
            burnout_risk_score=0.2
        )
        
        reliability_metrics = ReliabilityMetrics(
            acceptance_rate=0.76,
            completion_rate=0.95,
            ghost_rate=0.06,
            decline_after_accept_rate=0.02,
            reminder_effectiveness=0.88,
            communication_score=0.91,
            excuse_frequency=0.09
        )
        
        expertise_metrics = ExpertiseMetrics(
            expertise_areas=["machine learning", "computer vision", "optimization"],
            expertise_confidence={"machine learning": 0.92, "computer vision": 0.85, "optimization": 0.78},
            h_index=32,
            recent_publications=9,
            years_experience=14
        )
        
        metrics = RefereeMetrics(
            referee_id=str(uuid4()),
            name="Dr. Fixed Test",
            email="fixed.test@university.edu",
            institution="Fixed University",
            time_metrics=time_metrics,
            quality_metrics=quality_metrics,
            workload_metrics=workload_metrics,
            reliability_metrics=reliability_metrics,
            expertise_metrics=expertise_metrics
        )
        
        overall_score = metrics.get_overall_score()
        print(f"✅ Domain model created - Overall score: {overall_score:.2f}/10")
        tests_passed += 1
        
    except Exception as e:
        print(f"❌ Domain model creation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Save metrics (THE REAL TEST)
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Save referee metrics - THE MOMENT OF TRUTH")
    saved_id = None  # Initialize variable
    try:
        saved_id = await repo.save_referee_metrics(metrics)
        print(f"✅ ACTUALLY SAVED metrics! Referee ID: {saved_id}")
        tests_passed += 1
        
    except Exception as e:
        print(f"❌ Save failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Retrieve metrics
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Retrieve referee metrics")
    if saved_id:  # Only test if save succeeded
        try:
            retrieved = await repo.get_referee_metrics(saved_id)
            if retrieved:
                print(f"✅ ACTUALLY RETRIEVED metrics!")
                print(f"   Name: {retrieved.name}")
                print(f"   Email: {retrieved.email}")
                print(f"   Overall Score: {retrieved.get_overall_score():.2f}")
                print(f"   Data Completeness: {retrieved.data_completeness:.1%}")
                tests_passed += 1
            else:
                print("❌ Retrieved None")
                
        except Exception as e:
            print(f"❌ Retrieval failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ Skipping retrieval test - save failed")
    
    # Test 5: Get referee by email
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Get referee by email")
    try:
        referee = await repo.get_referee_by_email("fixed.test@university.edu")
        if referee:
            print(f"✅ Found referee by email: {referee.name}")
            print(f"   Institution: {referee.institution}")
            print(f"   H-index: {referee.h_index}")
            tests_passed += 1
        else:
            print("❌ Referee not found by email")
            
    except Exception as e:
        print(f"❌ Email lookup failed: {e}")
    
    # Test 6: Performance statistics
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Performance statistics")
    try:
        stats = await repo.get_performance_stats()
        print(f"✅ Got performance stats:")
        print(f"   Total referees: {stats.get('total_referees', 0)}")
        print(f"   Avg overall score: {stats.get('avg_overall_score', 0):.2f}")
        print(f"   Scored referees: {stats.get('scored_referees', 0)}")
        tests_passed += 1
        
    except Exception as e:
        print(f"❌ Performance stats failed: {e}")
    
    # Test 7: Top performers
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Top performers")
    try:
        performers = await repo.get_top_performers(limit=5)
        print(f"✅ Got top performers: {len(performers)} found")
        for i, performer in enumerate(performers, 1):
            print(f"   #{i}: {performer['name']} (Score: {performer['overall_score']:.2f})")
        tests_passed += 1
        
    except Exception as e:
        print(f"❌ Top performers failed: {e}")
    
    # Test 8: Record activity
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Record review activity")
    if saved_id:  # Only test if save succeeded
        try:
            success = await repo.record_review_activity(
                saved_id, 
                "review_completed", 
                {"score": 0.85, "current_reviews": 1}
            )
            if success:
                print("✅ Activity recorded successfully")
                tests_passed += 1
            else:
                print("❌ Activity recording returned False")
                
        except Exception as e:
            print(f"❌ Activity recording failed: {e}")
    else:
        print("❌ Skipping activity test - save failed")
    
    # Final Results
    print(f"\n{'='*60}")
    print(f"🎯 FIXED REPOSITORY TEST RESULTS")
    print(f"{'='*60}")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    print(f"Success rate: {tests_passed/total_tests:.1%}")
    
    if tests_passed == total_tests:
        print(f"\n🎉 ALL TESTS PASSED! 🎉")
        print(f"✅ The fixed repository is ACTUALLY FUNCTIONAL!")
        print(f"\n📋 Verified working features:")
        print(f"   ✅ Domain model creation and validation")
        print(f"   ✅ Referee metrics saving (complex serialization)")
        print(f"   ✅ Referee metrics retrieval (deserialization)")
        print(f"   ✅ Email-based referee lookup")
        print(f"   ✅ Performance statistics calculation")
        print(f"   ✅ Top performers ranking")
        print(f"   ✅ Review activity recording")
        print(f"\n🚀 REFEREE ANALYTICS IS NOW ACTUALLY WORKING!")
        return True
    else:
        print(f"\n❌ {total_tests - tests_passed} tests still failed")
        print(f"🔧 More fixes needed")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fixed_repository())
    sys.exit(0 if success else 1)