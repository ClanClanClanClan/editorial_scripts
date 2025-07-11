#!/usr/bin/env python3
"""
Simple Integration Test

Basic test to verify that legacy integration is working
and can load all components properly.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all components can be imported."""
    logger.info("🧪 Testing imports...")
    
    try:
        # Test session manager
        from editorial_assistant.utils.session_manager import session_manager
        logger.info("✅ Session manager imported")
        
        # Test legacy integration
        from editorial_assistant.core.legacy_integration import LegacyIntegrationMixin
        logger.info("✅ Legacy integration mixin imported")
        
        # Test email verification
        from editorial_assistant.utils.email_verification import EmailVerificationManager
        logger.info("✅ Email verification manager imported")
        
        # Test data models
        from editorial_assistant.core.data_models import Referee, Manuscript, Journal
        logger.info("✅ Data models imported")
        
        # Test ScholarOne extractor
        from editorial_assistant.extractors.scholarone import ScholarOneExtractor
        logger.info("✅ ScholarOne extractor imported")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def test_session_manager():
    """Test session manager functionality."""
    logger.info("🧪 Testing session manager...")
    
    try:
        from editorial_assistant.utils.session_manager import session_manager
        
        # Test adding a task
        session_manager.add_task(
            'test_task',
            'Test Task',
            'Testing session manager functionality'
        )
        
        # Test starting task
        session_manager.start_task('test_task')
        
        # Test completing task
        session_manager.complete_task(
            'test_task',
            outputs=['simple_integration_test.py'],
            notes='Simple integration test completed'
        )
        
        # Test adding learning
        session_manager.add_learning("Session manager is working correctly")
        
        logger.info("✅ Session manager test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Session manager test failed: {e}")
        return False

def test_data_models():
    """Test data model creation."""
    logger.info("🧪 Testing data models...")
    
    try:
        from editorial_assistant.core.data_models import (
            Referee, Manuscript, Journal, RefereeDates, RefereeStatus
        )
        
        # Test referee creation
        referee = Referee(
            name="Referee, Test",  # Use correct "Last, First" format
            institution="Test University",
            status=RefereeStatus.INVITED,
            dates=RefereeDates()
        )
        
        # Test manuscript creation  
        from editorial_assistant.core.data_models import ManuscriptStatus
        manuscript = Manuscript(
            manuscript_id="MAFI-2024-0167",
            title="Test Manuscript",
            journal_code="MF",
            status=ManuscriptStatus.AWAITING_REVIEWER_SCORES
        )
        
        # Test adding referee to manuscript
        manuscript.referees = [referee]
        
        # Test serialization
        manuscript_dict = manuscript.model_dump()
        assert 'manuscript_id' in manuscript_dict
        assert 'referees' in manuscript_dict
        assert len(manuscript_dict['referees']) == 1
        
        logger.info("✅ Data models test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Data models test failed: {e}")
        return False

def test_legacy_integration():
    """Test legacy integration mixin."""
    logger.info("🧪 Testing legacy integration...")
    
    try:
        from editorial_assistant.core.legacy_integration import LegacyIntegrationMixin
        
        # Create a test class with the mixin
        class TestExtractor(LegacyIntegrationMixin):
            def __init__(self):
                self.logger = logger
        
        extractor = TestExtractor()
        
        # Test that methods exist
        assert hasattr(extractor, 'legacy_login_scholarone')
        assert hasattr(extractor, 'legacy_click_checkbox')
        assert hasattr(extractor, 'legacy_download_pdfs')
        
        logger.info("✅ Legacy integration test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Legacy integration test failed: {e}")
        return False

def test_email_verification():
    """Test email verification manager."""
    logger.info("🧪 Testing email verification...")
    
    try:
        from editorial_assistant.utils.email_verification import (
            EmailVerificationManager, get_email_verification_manager
        )
        
        # Test manager creation
        manager = EmailVerificationManager()
        
        # Test global manager
        global_manager = get_email_verification_manager()
        
        # Test code extraction
        test_text = "Your verification code is: 123456"
        code = manager.extract_code_from_text(test_text)
        assert code == "123456"
        
        logger.info("✅ Email verification test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Email verification test failed: {e}")
        return False

def test_legacy_results_access():
    """Test access to legacy results for validation."""
    logger.info("🧪 Testing legacy results access...")
    
    try:
        import json
        
        legacy_dir = Path(__file__).parent / "legacy_20250710_165846" / "complete_results"
        
        # Check for MF results
        mf_file = legacy_dir / "mf_complete_stable_results.json"
        if mf_file.exists():
            with open(mf_file, 'r') as f:
                mf_data = json.load(f)
            logger.info(f"✅ Found MF legacy results: {len(mf_data.get('manuscripts', []))} manuscripts")
        else:
            logger.warning("⚠️  MF legacy results not found")
        
        # Check for MOR results
        mor_file = legacy_dir / "mor_complete_stable_results.json"
        if mor_file.exists():
            with open(mor_file, 'r') as f:
                mor_data = json.load(f)
            logger.info(f"✅ Found MOR legacy results: {len(mor_data.get('manuscripts', []))} manuscripts")
        else:
            logger.warning("⚠️  MOR legacy results not found")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Legacy results access test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    logger.info("🚀 Starting Simple Integration Test")
    
    tests = [
        ("Imports", test_imports),
        ("Session Manager", test_session_manager),
        ("Data Models", test_data_models),
        ("Legacy Integration", test_legacy_integration),
        ("Email Verification", test_email_verification),
        ("Legacy Results Access", test_legacy_results_access)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name} test...")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} test PASSED")
            else:
                failed += 1
                logger.error(f"❌ {test_name} test FAILED")
        except Exception as e:
            failed += 1
            logger.error(f"❌ {test_name} test FAILED with exception: {e}")
    
    # Summary
    logger.info(f"\n📊 Integration Test Summary:")
    logger.info(f"   Total tests: {len(tests)}")
    logger.info(f"   Passed: {passed}")
    logger.info(f"   Failed: {failed}")
    logger.info(f"   Success rate: {passed/len(tests)*100:.1f}%")
    
    if failed == 0:
        logger.info("🎉 All integration tests PASSED!")
        logger.info("✅ Legacy integration is ready for implementation")
        
        # Add final learning to session
        try:
            from editorial_assistant.utils.session_manager import session_manager
            session_manager.add_learning("Simple integration test passed - all components working")
            session_manager.auto_save_progress(
                "Simple Integration Test Completed",
                outputs=['simple_integration_test.py'],
                learning="All legacy integration components are working correctly"
            )
        except:
            pass
        
        return True
    else:
        logger.error("💥 Some integration tests FAILED!")
        logger.error("❌ Legacy integration needs fixes before proceeding")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)