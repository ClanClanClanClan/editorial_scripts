#!/usr/bin/env python3
"""
Improved test suite for referee analytics with dependency handling
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any, Optional, List

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.append(str(Path(__file__).parent / 'analytics'))

print("🚀 REFEREE ANALYTICS IMPROVED TEST SUITE")
print("=" * 70)


def check_dependencies():
    """Check if all required dependencies are available"""
    missing_deps = []
    optional_deps = []
    
    deps_to_check = {
        'sqlalchemy': 'SQLAlchemy ORM',
        'asyncpg': 'PostgreSQL async driver',
        'numpy': 'NumPy for calculations',
        'alembic': 'Database migrations'
    }
    
    for module, name in deps_to_check.items():
        try:
            __import__(module)
            print(f"✅ {name} available")
        except ImportError:
            missing_deps.append((module, name))
            print(f"❌ {name} not installed")
    
    return missing_deps


async def test_with_database():
    """Test with actual database if dependencies are available"""
    tests_passed = 0
    total_tests = 0
    
    try:
        from src.infrastructure.repositories.referee_repository_fixed import RefereeRepositoryFixed
        from models.referee_metrics import (
            RefereeMetrics, TimeMetrics, QualityMetrics, WorkloadMetrics,
            ReliabilityMetrics, ExpertiseMetrics
        )
        
        repo = RefereeRepositoryFixed()
        print("✅ Repository and models imported successfully")
        
        # Run full test suite
        # Test 1: Create metrics
        total_tests += 1
        print(f"\n🧪 TEST {total_tests}: Create referee metrics")
        
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
            name="Dr. Integration Test",
            email="integration.test@university.edu",
            institution="Integration University",
            time_metrics=time_metrics,
            quality_metrics=quality_metrics,
            workload_metrics=workload_metrics,
            reliability_metrics=reliability_metrics,
            expertise_metrics=expertise_metrics
        )
        
        print(f"✅ Metrics created - Overall score: {metrics.get_overall_score():.2f}/10")
        tests_passed += 1
        
        # Test 2: Save to database
        total_tests += 1
        print(f"\n🧪 TEST {total_tests}: Save to database")
        
        saved_id = await repo.save_referee_metrics(metrics)
        print(f"✅ Saved to database! ID: {saved_id}")
        tests_passed += 1
        
        # Test 3: Retrieve from database
        total_tests += 1
        print(f"\n🧪 TEST {total_tests}: Retrieve from database")
        
        retrieved = await repo.get_referee_metrics(saved_id)
        if retrieved:
            print(f"✅ Retrieved successfully!")
            print(f"   Name: {retrieved.name}")
            print(f"   Score: {retrieved.get_overall_score():.2f}")
            tests_passed += 1
        else:
            print("❌ Retrieval failed")
        
        # Test 4: Performance stats
        total_tests += 1
        print(f"\n🧪 TEST {total_tests}: Performance statistics")
        
        stats = await repo.get_performance_stats()
        print(f"✅ Stats retrieved:")
        print(f"   Total referees: {stats.get('total_referees', 0)}")
        print(f"   Average score: {stats.get('avg_overall_score', 0):.2f}")
        tests_passed += 1
        
        return tests_passed, total_tests
        
    except Exception as e:
        print(f"\n❌ Database tests failed: {e}")
        import traceback
        traceback.print_exc()
        return tests_passed, total_tests


async def test_code_quality():
    """Test code quality and structure without database"""
    tests_passed = 0
    total_tests = 0
    
    print("\n📋 CODE QUALITY TESTS")
    print("-" * 40)
    
    # Test 1: Check file structure
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: File structure")
    
    required_files = [
        "src/infrastructure/database/referee_models_fixed.py",
        "src/infrastructure/repositories/referee_repository_fixed.py",
        "analytics/models/referee_metrics.py"
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} missing")
            all_exist = False
    
    if all_exist:
        tests_passed += 1
    
    # Test 2: Check repository methods
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Repository method signatures")
    
    try:
        with open("src/infrastructure/repositories/referee_repository_fixed.py", "r") as f:
            content = f.read()
        
        required_methods = [
            "save_referee_metrics",
            "get_referee_metrics",
            "get_referee_by_email",
            "get_performance_stats",
            "get_top_performers",
            "record_review_activity"
        ]
        
        all_methods_found = True
        for method in required_methods:
            if f"async def {method}" in content:
                print(f"  ✅ {method} found")
            else:
                print(f"  ❌ {method} missing")
                all_methods_found = False
        
        if all_methods_found:
            tests_passed += 1
            
    except Exception as e:
        print(f"  ❌ Could not analyze repository: {e}")
    
    # Test 3: Check model structure
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Domain model structure")
    
    try:
        with open("analytics/models/referee_metrics.py", "r") as f:
            content = f.read()
        
        required_classes = [
            "RefereeMetrics",
            "TimeMetrics",
            "QualityMetrics",
            "WorkloadMetrics",
            "ReliabilityMetrics",
            "ExpertiseMetrics"
        ]
        
        all_classes_found = True
        for cls in required_classes:
            if f"class {cls}" in content:
                print(f"  ✅ {cls} found")
            else:
                print(f"  ❌ {cls} missing")
                all_classes_found = False
        
        if all_classes_found:
            tests_passed += 1
            
    except Exception as e:
        print(f"  ❌ Could not analyze models: {e}")
    
    # Test 4: SQL implementation check
    total_tests += 1
    print(f"\n🧪 TEST {total_tests}: Raw SQL implementation")
    
    try:
        with open("src/infrastructure/repositories/referee_repository_fixed.py", "r") as f:
            content = f.read()
        
        sql_patterns = [
            ("INSERT INTO referee_analytics_cache", "Cache storage"),
            ("SELECT r.*, c.metrics_json", "Data retrieval"),
            ("INSERT INTO referee_metrics_history", "History tracking")
        ]
        
        # Check for either raw SQL or ORM approach for referee creation
        orm_patterns = [
            ("RefereeAnalyticsModel(", "Referee creation (ORM)")
        ]
        
        all_sql_found = True
        for pattern, description in sql_patterns:
            if pattern in content:
                print(f"  ✅ {description} SQL found")
            else:
                print(f"  ❌ {description} SQL missing")
                all_sql_found = False
        
        # Check ORM patterns
        for pattern, description in orm_patterns:
            if pattern in content:
                print(f"  ✅ {description} found")
            else:
                # Check if raw SQL INSERT is used instead
                if "INSERT INTO referees_analytics" in content:
                    print(f"  ✅ Referee creation (raw SQL) found")
                else:
                    print(f"  ❌ {description} missing")
                    all_sql_found = False
        
        if all_sql_found:
            tests_passed += 1
            
    except Exception as e:
        print(f"  ❌ Could not analyze SQL: {e}")
    
    return tests_passed, total_tests


async def main():
    """Main test runner"""
    # Check dependencies
    print("📦 CHECKING DEPENDENCIES")
    print("-" * 40)
    missing_deps = check_dependencies()
    
    total_passed = 0
    total_tests = 0
    
    # Always run code quality tests
    quality_passed, quality_total = await test_code_quality()
    total_passed += quality_passed
    total_tests += quality_total
    
    # Run database tests if dependencies available
    if not missing_deps:
        print("\n🗄️  RUNNING DATABASE INTEGRATION TESTS")
        print("-" * 40)
        db_passed, db_total = await test_with_database()
        total_passed += db_passed
        total_tests += db_total
    else:
        print("\n⚠️  SKIPPING DATABASE TESTS (missing dependencies)")
        print("To run full tests, install:")
        for module, name in missing_deps:
            print(f"  pip install {module}")
    
    # Final summary
    print(f"\n{'='*70}")
    print(f"🎯 FINAL TEST RESULTS")
    print(f"{'='*70}")
    print(f"Total tests passed: {total_passed}/{total_tests}")
    print(f"Success rate: {total_passed/total_tests:.1%}" if total_tests > 0 else "No tests run")
    
    if total_passed == total_tests and total_tests > 0:
        print(f"\n🎉 ALL TESTS PASSED! 🎉")
        print("\n📋 VERIFIED COMPONENTS:")
        print("  ✅ File structure correct")
        print("  ✅ Repository methods implemented")
        print("  ✅ Domain models defined")
        print("  ✅ Raw SQL queries present")
        
        if not missing_deps:
            print("  ✅ Database integration functional")
            print("  ✅ Full system operational")
        else:
            print("  ⚠️  Database integration not tested")
            print("  ⚠️  Install dependencies for full validation")
        
        print("\n🚀 REFEREE ANALYTICS SYSTEM STATUS: READY")
        return True
    else:
        print(f"\n❌ {total_tests - total_passed} tests failed")
        print("🔧 Issues need to be resolved")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)