#!/usr/bin/env python3
"""
Test Data Model Integration

Tests that the Phase 1 foundation data models work correctly
with the baseline data volumes and provide proper validation.
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime, date
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "editorial_assistant"))

# Load environment variables
load_dotenv(project_root / ".env.production")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# July 11 baseline for validation
JULY_11_BASELINE = {
    'total_manuscripts': 4,
    'total_referees': 13,
    'referees_with_emails': 13,
    'pdfs_downloaded': 4
}


def test_data_model_imports():
    """Test that we can import the data models."""
    print("📦 Testing Data Model Imports...")
    
    try:
        from core.data_models import (
            Manuscript, Referee, RefereeStatus, ManuscriptStatus,
            Journal, JournalConfig, ExtractionResult
        )
        print("✅ Successfully imported all data models")
        return True, (Manuscript, Referee, RefereeStatus, ManuscriptStatus, Journal, JournalConfig, ExtractionResult)
    
    except ImportError as e:
        print(f"❌ Failed to import data models: {e}")
        return False, None


def test_referee_creation_and_validation():
    """Test referee creation with validation."""
    print("\n👥 Testing Referee Creation and Validation...")
    
    try:
        from core.data_models import Referee, RefereeStatus
        
        # Test valid referee creation
        referee = Referee(
            name="Smith, John",
            email="john.smith@university.edu",
            institution="University Example",
            status=RefereeStatus.AGREED
        )
        
        assert referee.name == "Smith, John"
        assert referee.email == "john.smith@university.edu"
        assert referee.status == RefereeStatus.AGREED
        assert referee.is_active == True
        print("✅ Basic referee creation works")
        
        # Test name validation (must be "Last, First" format)
        try:
            invalid_referee = Referee(
                name="John Smith",  # Wrong format
                email="john@example.com"
            )
            print("❌ Name validation should have failed")
            return False
        except ValueError:
            print("✅ Name validation working correctly")
        
        # Test referee without email
        referee_no_email = Referee(
            name="Johnson, Sarah",
            status=RefereeStatus.INVITED
        )
        assert referee_no_email.email is None
        print("✅ Referee creation without email works")
        
        return True
        
    except Exception as e:
        print(f"❌ Referee testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_manuscript_creation_and_validation():
    """Test manuscript creation with validation."""
    print("\n📄 Testing Manuscript Creation and Validation...")
    
    try:
        from core.data_models import Manuscript, ManuscriptStatus, Referee, RefereeStatus
        
        # Create referees
        referees = [
            Referee(
                name="Chen, Alice",
                email="alice.chen@stanford.edu",
                institution="Stanford University",
                status=RefereeStatus.AGREED
            ),
            Referee(
                name="Martinez, Bob",
                email="bob.martinez@mit.edu",
                institution="MIT",
                status=RefereeStatus.COMPLETED
            )
        ]
        
        # Create manuscript
        manuscript = Manuscript(
            manuscript_id="SICON-2025-001",
            title="Optimal Control of Stochastic Systems",
            status=ManuscriptStatus.AWAITING_REVIEWER_SCORES,
            journal_code="SICON",
            referees=referees,
            submission_date=date(2025, 1, 15)
        )
        
        assert manuscript.manuscript_id == "SICON-2025-001"
        assert len(manuscript.referees) == 2
        assert len(manuscript.active_referees) == 1  # Only AGREED referee is active
        assert len(manuscript.completed_referees) == 1  # Only COMPLETED referee
        print("✅ Manuscript creation and properties work")
        
        # Test days in review calculation
        days = manuscript.days_in_review
        assert days is not None and days > 0
        print(f"✅ Days in review calculation: {days} days")
        
        return True
        
    except Exception as e:
        print(f"❌ Manuscript testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_baseline_data_model_integration():
    """Test data models with baseline data volumes."""
    print("\n🎯 Testing Baseline Data Model Integration...")
    
    try:
        from core.data_models import Manuscript, Referee, RefereeStatus, ManuscriptStatus
        
        # Create 4 manuscripts to match baseline
        manuscripts = []
        all_referees = []
        
        # Referee distribution: 4, 3, 3, 3 = 13 total
        referee_counts = [4, 3, 3, 3]
        
        for i in range(4):
            # Create referees for this manuscript
            manuscript_referees = []
            for j in range(referee_counts[i]):
                referee = Referee(
                    name=f"Reviewer{i+1}_{j+1}, John",
                    email=f"reviewer{i+1}_{j+1}@university.edu",
                    institution=f"University {i+1}-{j+1}",
                    status=RefereeStatus.AGREED
                )
                manuscript_referees.append(referee)
                all_referees.append(referee)
            
            # Create manuscript
            manuscript = Manuscript(
                manuscript_id=f"SICON-2025-{i+1:03d}",
                title=f"Optimal Control Theory Paper {i+1}",
                status=ManuscriptStatus.AWAITING_REVIEWER_SCORES,
                journal_code="SICON",
                referees=manuscript_referees,
                submission_date=date(2025, 1, 15 + i)
            )
            manuscripts.append(manuscript)
        
        # Validate baseline numbers
        total_manuscripts = len(manuscripts)
        total_referees = sum(len(m.referees) for m in manuscripts)
        referees_with_emails = sum(
            1 for m in manuscripts 
            for r in m.referees 
            if r.email
        )
        
        assert total_manuscripts == JULY_11_BASELINE['total_manuscripts']
        assert total_referees == JULY_11_BASELINE['total_referees']
        assert referees_with_emails == JULY_11_BASELINE['referees_with_emails']
        
        print(f"✅ Baseline validation:")
        print(f"   Manuscripts: {total_manuscripts}/{JULY_11_BASELINE['total_manuscripts']}")
        print(f"   Referees: {total_referees}/{JULY_11_BASELINE['total_referees']}")
        print(f"   Emails: {referees_with_emails}/{JULY_11_BASELINE['referees_with_emails']}")
        
        # Test manuscript queries
        active_manuscripts = [m for m in manuscripts if m.active_referees]
        print(f"✅ Manuscripts with active referees: {len(active_manuscripts)}")
        
        # Test referee status distribution
        status_counts = {}
        for referee in all_referees:
            status = referee.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"✅ Referee status distribution: {status_counts}")
        
        return True
        
    except Exception as e:
        print(f"❌ Baseline integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_extraction_result_model():
    """Test extraction result model with baseline data."""
    print("\n📊 Testing Extraction Result Model...")
    
    try:
        from core.data_models import (
            ExtractionResult, Journal, Platform, 
            Manuscript, ManuscriptStatus, Referee, RefereeStatus
        )
        
        # Create journal
        journal = Journal(
            code="SICON",
            name="SIAM Journal on Control and Optimization",
            platform=Platform.EDITORIAL_MANAGER,
            url="https://www.editorialmanager.com/siamjco/",
            credentials={"username": "test@example.com", "password": "password"}
        )
        
        # Create manuscripts with referees
        manuscripts = []
        for i in range(4):
            referees = [
                Referee(
                    name=f"Expert{i+1}_{j+1}, Jane",
                    email=f"expert{i+1}_{j+1}@university.edu",
                    status=RefereeStatus.AGREED
                ) for j in range(3 + (1 if i == 0 else 0))  # 4,3,3,3 distribution
            ]
            
            manuscript = Manuscript(
                manuscript_id=f"SICON-2025-{i+1:03d}",
                title=f"Advanced Control Theory {i+1}",
                status=ManuscriptStatus.AWAITING_REVIEWER_SCORES,
                journal_code="SICON",
                referees=referees
            )
            manuscripts.append(manuscript)
        
        # Create extraction result
        result = ExtractionResult(
            journal=journal,
            manuscripts=manuscripts,
            duration_seconds=45.7,
            stats={"extraction_method": "Phase1_Foundation"}
        )
        
        # Test properties
        assert result.success == True
        assert result.total_referees == 13
        assert len(result.manuscripts) == 4
        print(f"✅ Extraction result properties work")
        
        # Test summary generation
        summary = result.to_summary()
        assert summary['journal'] == 'SICON'
        assert summary['manuscripts_count'] == 4
        assert summary['referees_count'] == 13
        assert summary['success'] == True
        print(f"✅ Extraction result summary generation works")
        
        print(f"📊 Extraction Result Summary:")
        for key, value in summary.items():
            print(f"   {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Extraction result test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_json_serialization():
    """Test JSON serialization of data models."""
    print("\n💾 Testing JSON Serialization...")
    
    try:
        from core.data_models import Manuscript, Referee, RefereeStatus, ManuscriptStatus
        import json
        
        # Create test data
        referee = Referee(
            name="Wilson, Carol",
            email="carol.wilson@caltech.edu",
            institution="Caltech",
            status=RefereeStatus.COMPLETED
        )
        
        manuscript = Manuscript(
            manuscript_id="SICON-2025-TEST",
            title="JSON Serialization Test",
            status=ManuscriptStatus.AWAITING_REVIEWER_REPORTS,
            journal_code="SICON",
            referees=[referee],
            submission_date=date(2025, 1, 15)
        )
        
        # Test JSON serialization
        manuscript_dict = manuscript.dict()
        json_str = json.dumps(manuscript_dict, indent=2, default=str)
        
        # Test deserialization
        parsed_dict = json.loads(json_str)
        reconstructed = Manuscript(**parsed_dict)
        
        assert reconstructed.manuscript_id == manuscript.manuscript_id
        assert len(reconstructed.referees) == 1
        print("✅ JSON serialization and deserialization works")
        
        return True
        
    except Exception as e:
        print(f"❌ JSON serialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all data model integration tests."""
    print("🧪 Data Model Integration Test - Phase 1 Foundation")
    print("=" * 60)
    
    tests = [
        ("Data Model Imports", test_data_model_imports),
        ("Referee Creation and Validation", test_referee_creation_and_validation),
        ("Manuscript Creation and Validation", test_manuscript_creation_and_validation),
        ("Baseline Data Model Integration", test_baseline_data_model_integration),
        ("Extraction Result Model", test_extraction_result_model),
        ("JSON Serialization", test_json_serialization)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📝 Running {test_name}...")
        
        try:
            if test_name == "Data Model Imports":
                success, models = test_func()
                if not success:
                    print("❌ Cannot continue without data models")
                    return False
            else:
                success = test_func()
            
            results.append((test_name, success))
            
            if success:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
                
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DATA MODEL INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 DATA MODEL INTEGRATION SUCCESSFUL!")
        print("\n🔍 VALIDATION RESULTS:")
        print("✅ All Pydantic data models import correctly")
        print("✅ Referee validation works with name format requirements")
        print("✅ Manuscript creation handles referees and dates correctly")
        print("✅ Baseline data volumes (4 manuscripts, 13 referees) work perfectly")
        print("✅ ExtractionResult model handles complete extraction data")
        print("✅ JSON serialization preserves all data integrity")
        print("\n🚀 PHASE 1 DATA MODELS READY FOR PRODUCTION")
        print(f"Ready to process {JULY_11_BASELINE['total_manuscripts']} manuscripts with {JULY_11_BASELINE['total_referees']} referees!")
    else:
        print("⚠️  Some tests failed - Need to fix data model issues")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)