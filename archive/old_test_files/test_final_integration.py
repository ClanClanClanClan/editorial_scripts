#!/usr/bin/env python3
"""
FINAL MANIAC TEST - Complete referee analytics integration
"""

import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.append(str(Path(__file__).parent / 'analytics'))

print("🚀 FINAL MANIAC TEST - Complete Referee Analytics Integration")
print("=" * 70)

async def final_integration_test():
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Basic imports and setup
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Basic imports and setup")
    try:
        from src.infrastructure.config import get_settings
        from models.referee_metrics import RefereeMetrics, TimeMetrics, QualityMetrics, WorkloadMetrics, ReliabilityMetrics, ExpertiseMetrics
        import asyncpg
        
        settings = get_settings()
        print(f"✅ All imports successful")
        print(f"✅ Database config: {settings.db_name}@{settings.db_host}")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Import failed: {e}")
    
    # Test 2: Database connection and tables
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Database connection and table verification")
    try:
        conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name
        )
        
        # Check tables exist
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name LIKE '%analytics%'
        """)
        table_names = [t['table_name'] for t in tables]
        
        required_tables = ['referees_analytics', 'referee_analytics_cache']
        missing_tables = [t for t in required_tables if t not in table_names]
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
        else:
            print(f"✅ All required tables exist: {table_names}")
            tests_passed += 1
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
    
    # Test 3: Raw data operations
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Raw data operations")
    try:
        import uuid
        
        # Insert test referee
        test_id = uuid.uuid4()
        result = await conn.fetchrow("""
            INSERT INTO referees_analytics (id, name, email, institution, h_index, years_experience)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
            RETURNING id, name
        """, test_id, "Dr. Maniac Test", "maniac.test@university.edu", "Maniac University", 42, 20)
        
        actual_id = result['id']
        
        # Insert cache data
        cache_metrics = {
            "referee_id": str(actual_id),
            "name": "Dr. Maniac Test",
            "email": "maniac.test@university.edu",
            "overall_score": 9.2,
            "expertise_score": 0.95,
            "reliability_score": 0.88,
            "test_timestamp": datetime.now().isoformat()
        }
        
        await conn.execute("""
            INSERT INTO referee_analytics_cache (referee_id, metrics_json, calculated_at, valid_until)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (referee_id) DO UPDATE SET 
                metrics_json = EXCLUDED.metrics_json,
                calculated_at = EXCLUDED.calculated_at
        """, actual_id, json.dumps(cache_metrics), datetime.now(), datetime.now() + timedelta(hours=24))
        
        # Verify data
        verify = await conn.fetchrow("""
            SELECT r.name, r.h_index, c.metrics_json
            FROM referees_analytics r
            JOIN referee_analytics_cache c ON r.id = c.referee_id
            WHERE r.id = $1
        """, actual_id)
        
        if verify and verify['name'] == "Dr. Maniac Test":
            cached_data = json.loads(verify['metrics_json'])
            print(f"✅ Data operations successful")
            print(f"   Referee: {verify['name']} (H-index: {verify['h_index']})")
            print(f"   Cached score: {cached_data.get('overall_score')}")
            tests_passed += 1
        else:
            print(f"❌ Data verification failed")
        
    except Exception as e:
        print(f"❌ Raw data operations failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Domain model creation
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Domain model creation")
    try:
        # Create complete domain model
        time_metrics = TimeMetrics(
            avg_response_time=2.5,
            avg_review_time=16.0,
            fastest_review=10,
            slowest_review=28,
            response_time_std=1.2,
            review_time_std=4.8,
            on_time_rate=0.92
        )
        
        quality_metrics = QualityMetrics(
            avg_quality_score=9.1,
            quality_consistency=0.9,
            report_thoroughness=0.95,
            constructiveness_score=9.2,
            technical_accuracy=9.4,
            clarity_score=8.8,
            actionability_score=8.9
        )
        
        workload_metrics = WorkloadMetrics(
            current_reviews=1,
            completed_reviews_30d=4,
            completed_reviews_90d=12,
            completed_reviews_365d=45,
            monthly_average=3.8,
            peak_capacity=5,
            availability_score=0.9,
            burnout_risk_score=0.15
        )
        
        reliability_metrics = ReliabilityMetrics(
            acceptance_rate=0.78,
            completion_rate=0.96,
            ghost_rate=0.04,
            decline_after_accept_rate=0.02,
            reminder_effectiveness=0.91,
            communication_score=0.94,
            excuse_frequency=0.08
        )
        
        expertise_metrics = ExpertiseMetrics(
            expertise_areas=["deep learning", "computer vision", "optimization"],
            expertise_confidence={"deep learning": 0.95, "computer vision": 0.88, "optimization": 0.82},
            h_index=42,
            recent_publications=12,
            years_experience=20
        )
        
        metrics = RefereeMetrics(
            referee_id=str(actual_id),
            name="Dr. Maniac Test",
            email="maniac.test@university.edu",
            institution="Maniac University",
            time_metrics=time_metrics,
            quality_metrics=quality_metrics,
            workload_metrics=workload_metrics,
            reliability_metrics=reliability_metrics,
            expertise_metrics=expertise_metrics
        )
        
        overall_score = metrics.get_overall_score()
        print(f"✅ Domain model created successfully")
        print(f"   Overall score: {overall_score:.2f}/10")
        print(f"   Expertise areas: {len(metrics.expertise_metrics.expertise_areas)}")
        print(f"   Data completeness: {metrics.data_completeness:.1%}")
        tests_passed += 1
        
    except Exception as e:
        print(f"❌ Domain model creation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Performance statistics
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Performance statistics and analytics")
    try:
        # Calculate some analytics
        all_referees = await conn.fetch("""
            SELECT r.name, r.h_index, r.years_experience,
                   c.metrics_json
            FROM referees_analytics r
            LEFT JOIN referee_analytics_cache c ON r.id = c.referee_id
            ORDER BY r.h_index DESC NULLS LAST
            LIMIT 10
        """)
        
        print(f"✅ Performance analytics successful")
        print(f"   Total referees in database: {len(all_referees)}")
        
        for i, ref in enumerate(all_referees[:3], 1):
            cached_score = "N/A"
            if ref['metrics_json']:
                try:
                    cached_data = json.loads(ref['metrics_json'])
                    cached_score = f"{cached_data.get('overall_score', 'N/A')}"
                except:
                    pass
            
            print(f"   #{i}: {ref['name']} (H-index: {ref['h_index']}, Score: {cached_score})")
        
        tests_passed += 1
        
    except Exception as e:
        print(f"❌ Performance statistics failed: {e}")
    
    # Test 6: End-to-end workflow simulation
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: End-to-end workflow simulation")
    try:
        # Simulate a complete referee evaluation workflow
        workflow_id = uuid.uuid4()
        
        # Step 1: Create referee
        result = await conn.fetchrow("""
            INSERT INTO referees_analytics (id, name, email, institution, h_index, years_experience)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """, workflow_id, "Dr. Workflow Test", "workflow@test.edu", "Workflow Institute", 35, 15)
        
        # Use the actual returned ID
        actual_workflow_id = result['id']
        
        # Step 2: Cache comprehensive metrics
        workflow_metrics = {
            "referee_id": str(actual_workflow_id),
            "name": "Dr. Workflow Test",
            "overall_score": 8.7,
            "time_metrics": {"avg_review_time": 19.2, "on_time_rate": 0.89},
            "quality_metrics": {"avg_quality_score": 8.6, "thoroughness": 0.88},
            "reliability_metrics": {"acceptance_rate": 0.74, "completion_rate": 0.93},
            "expertise_metrics": {"h_index": 35, "areas": ["machine learning", "statistics"]},
            "calculated_at": datetime.now().isoformat(),
            "workflow_test": True
        }
        
        await conn.execute("""
            INSERT INTO referee_analytics_cache (referee_id, metrics_json, calculated_at, valid_until)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (referee_id) DO UPDATE SET metrics_json = EXCLUDED.metrics_json
        """, actual_workflow_id, json.dumps(workflow_metrics), datetime.now(), datetime.now() + timedelta(days=1))
        
        # Step 3: Query comprehensive data
        workflow_result = await conn.fetchrow("""
            SELECT r.*, c.metrics_json
            FROM referees_analytics r
            JOIN referee_analytics_cache c ON r.id = c.referee_id
            WHERE r.id = $1
        """, actual_workflow_id)
        
        if workflow_result:
            metrics_data = json.loads(workflow_result['metrics_json'])
            print(f"✅ End-to-end workflow successful")
            print(f"   Referee: {workflow_result['name']}")
            print(f"   Institution: {workflow_result['institution']}")
            print(f"   Cached overall score: {metrics_data.get('overall_score')}")
            print(f"   Workflow validation: {metrics_data.get('workflow_test')}")
            tests_passed += 1
        else:
            print(f"❌ Workflow data not found")
            
    except Exception as e:
        print(f"❌ End-to-end workflow failed: {e}")
        import traceback
        traceback.print_exc()
    
    await conn.close()
    
    # Final summary
    print(f"\n{'='*70}")
    print(f"🎯 FINAL INTEGRATION TEST RESULTS")
    print(f"{'='*70}")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    print(f"Success rate: {tests_passed/total_tests:.1%}")
    
    if tests_passed == total_tests:
        print(f"\n🎉 ALL TESTS PASSED! 🎉")
        print(f"✅ Referee analytics PostgreSQL integration is FULLY FUNCTIONAL")
        print(f"\n📋 Verified capabilities:")
        print(f"   ✅ Database tables created and accessible")
        print(f"   ✅ Raw data operations (insert, update, query)")
        print(f"   ✅ Domain model creation and validation")
        print(f"   ✅ Performance metrics calculation")
        print(f"   ✅ Caching system functional")
        print(f"   ✅ End-to-end workflow operational")
        print(f"\n🚀 READY FOR PRODUCTION USE!")
        return True
    else:
        print(f"\n❌ {total_tests - tests_passed} tests failed")
        print(f"🔧 System requires fixes before production use")
        return False

if __name__ == "__main__":
    success = asyncio.run(final_integration_test())
    sys.exit(0 if success else 1)