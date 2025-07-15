#!/usr/bin/env python3
"""
Quick Foundation Test Runner

Tests the Phase 1 foundation components without requiring full pytest setup.
This allows immediate validation of the new architecture.
"""

import sys
import asyncio
import traceback
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test imports
def test_imports():
    """Test that all Phase 1 components can be imported."""
    print("🔍 Testing Phase 1 imports...")
    
    try:
        # Authentication imports
        from editorial_assistant.core.authentication import (
            AuthenticationProvider, ORCIDAuth, ScholarOneAuth, EditorialManagerAuth,
            AuthStatus, AuthenticationResult
        )
        print("✅ Authentication components imported successfully")
        
        # Browser imports  
        from editorial_assistant.core.browser import (
            BrowserSession, BrowserPool, BrowserConfig, BrowserType
        )
        print("✅ Browser components imported successfully")
        
        # Extraction imports
        from editorial_assistant.core.extraction import (
            ExtractionContract, ExtractionResult, QualityValidator,
            ExtractionStatus, QualityScore, DataQualityMetrics
        )
        print("✅ Extraction components imported successfully")
        
        # Data models import
        from editorial_assistant.core.data_models import Manuscript, Referee
        print("✅ Data models imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False


def test_authentication_providers():
    """Test authentication provider initialization and validation."""
    print("\n🔐 Testing Authentication Providers...")
    
    try:
        from editorial_assistant.core.authentication import ORCIDAuth, ScholarOneAuth, EditorialManagerAuth
        
        # Test ORCID Auth
        credentials = {'username': 'test@example.com', 'password': 'test123'}
        orcid_auth = ORCIDAuth('SICON', credentials)
        
        assert orcid_auth.journal_code == 'SICON'
        assert orcid_auth.get_login_url() == 'https://www.editorialmanager.com/siamjco/'
        assert orcid_auth.validate_credentials() == True
        print("✅ ORCID authentication provider working")
        
        # Test ScholarOne Auth
        so_auth = ScholarOneAuth('MF', credentials)
        assert so_auth.journal_code == 'MF'
        assert so_auth.get_login_url() == 'https://mc.manuscriptcentral.com/mafi'
        assert so_auth.validate_credentials() == True
        print("✅ ScholarOne authentication provider working")
        
        # Test Editorial Manager Auth
        em_auth = EditorialManagerAuth('FS', credentials)
        assert em_auth.journal_code == 'FS'
        assert em_auth.get_login_url() == 'https://www.editorialmanager.com/finsto/'
        assert em_auth.validate_credentials() == True
        print("✅ Editorial Manager authentication provider working")
        
        # Test credential validation
        invalid_credentials = {'username': 'test@example.com'}  # Missing password
        invalid_auth = ORCIDAuth('SICON', invalid_credentials)
        assert invalid_auth.validate_credentials() == False
        print("✅ Credential validation working")
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        traceback.print_exc()
        return False


def test_browser_configuration():
    """Test browser configuration and session management."""
    print("\n🖥️  Testing Browser Management...")
    
    try:
        from editorial_assistant.core.browser import BrowserConfig, BrowserType, BrowserSession, BrowserPool
        
        # Test default configuration
        config = BrowserConfig()
        assert config.browser_type == BrowserType.UNDETECTED_CHROME
        assert config.headless == True
        assert config.window_size == (1920, 1080)
        print("✅ Default browser configuration working")
        
        # Test stealth mode
        stealth_config = BrowserConfig.for_stealth_mode()
        assert stealth_config.browser_type == BrowserType.UNDETECTED_CHROME
        chrome_options = stealth_config.get_chrome_options()
        assert "--disable-blink-features=AutomationControlled" in chrome_options
        print("✅ Stealth mode configuration working")
        
        # Test performance mode
        perf_config = BrowserConfig.for_performance()
        assert perf_config.disable_images == True
        assert perf_config.disable_gpu == True
        print("✅ Performance mode configuration working")
        
        # Test browser session initialization
        session = BrowserSession(config)
        assert session.config == config
        assert session.driver is None
        assert session._is_initialized == False
        print("✅ Browser session initialization working")
        
        # Test browser pool initialization
        pool = BrowserPool(pool_size=2, config=config)
        assert pool.pool_size == 2
        assert pool.config == config
        assert pool._is_initialized == False
        print("✅ Browser pool initialization working")
        
        return True
        
    except Exception as e:
        print(f"❌ Browser test failed: {e}")
        traceback.print_exc()
        return False


def test_extraction_contract():
    """Test extraction contract and quality validation."""
    print("\n📋 Testing Extraction Contract...")
    
    try:
        from editorial_assistant.core.extraction import (
            ExtractionContract, QualityScore, DataQualityMetrics, 
            QualityValidator, ExtractionStatus
        )
        from editorial_assistant.core.data_models import Manuscript, Referee
        
        # Test contract initialization
        contract = ExtractionContract('SICON', 'SIAM Journal on Control and Optimization')
        assert contract.journal_code == 'SICON'
        assert contract.journal_name == 'SIAM Journal on Control and Optimization'
        assert contract.minimum_quality_threshold == 0.7
        print("✅ Extraction contract initialization working")
        
        # Test contract lifecycle
        contract.begin_extraction({'headless': True})
        assert contract._extraction_started == True
        
        contract.complete_extraction()
        assert contract._extraction_completed == True
        assert contract.metadata.duration_seconds >= 0
        print("✅ Extraction contract lifecycle working")
        
        # Test quality score calculation
        score = QualityScore()
        score.manuscript_completeness = 0.8
        score.referee_completeness = 0.6
        score.pdf_success_rate = 0.7
        score.data_integrity = 0.9
        score.has_referee_emails = True
        
        overall = score.calculate_overall_score()
        assert 0.0 <= overall <= 1.0
        print("✅ Quality score calculation working")
        
        # Test data quality metrics
        metrics = DataQualityMetrics()
        metrics.total_manuscripts_found = 10
        metrics.total_manuscripts_processed = 9
        metrics.total_referees_found = 20
        metrics.total_referees_with_emails = 15
        
        rates = metrics.calculate_success_rates()
        assert rates['manuscript_processing_rate'] == 0.9
        assert rates['email_extraction_rate'] == 0.75
        print("✅ Data quality metrics working")
        
        # Test extraction result creation
        manuscripts = [
            Manuscript(manuscript_id="TEST-2025-001", title="Test Paper 1"),
            Manuscript(manuscript_id="TEST-2025-002", title="Test Paper 2")
        ]
        
        referees = [
            Referee(name="Dr. Test Reviewer", email="test@example.com")
        ]
        
        contract2 = ExtractionContract('TEST', 'Test Journal')
        result = contract2.create_result(manuscripts, referees)
        
        assert len(result.manuscripts) == 2
        assert len(result.referees) == 1
        assert result.metadata is not None
        assert result.quality_score is not None
        print("✅ Extraction result creation working")
        
        # Test quality validator
        validator = QualityValidator()
        validation = validator.validate_extraction_result(result)
        
        assert hasattr(validation, 'is_valid')
        assert hasattr(validation, 'summary')
        assert isinstance(validation.recommendations, list)
        print("✅ Quality validation working")
        
        return True
        
    except Exception as e:
        print(f"❌ Extraction contract test failed: {e}")
        traceback.print_exc()
        return False


async def test_async_functionality():
    """Test async functionality in browser management."""
    print("\n⚡ Testing Async Functionality...")
    
    try:
        from editorial_assistant.core.browser import BrowserConfig, BrowserSession, BrowserPool
        
        # Test browser session async context manager structure
        config = BrowserConfig()
        session = BrowserSession(config)
        
        # Test that async methods exist
        assert hasattr(session, '__aenter__')
        assert hasattr(session, '__aexit__')
        assert hasattr(session, 'initialize')
        assert hasattr(session, 'cleanup')
        print("✅ Browser session async interface working")
        
        # Test browser pool async methods
        pool = BrowserPool(pool_size=2, config=config)
        
        # Test health check (doesn't require initialization)
        health = await pool.health_check()
        assert 'pool_size' in health
        assert 'is_healthy' in health
        print("✅ Browser pool async interface working")
        
        return True
        
    except Exception as e:
        print(f"❌ Async functionality test failed: {e}")
        traceback.print_exc()
        return False


def test_integration():
    """Test integration between Phase 1 components."""
    print("\n🔗 Testing Component Integration...")
    
    try:
        from editorial_assistant.core.authentication import ORCIDAuth
        from editorial_assistant.core.browser import BrowserConfig, BrowserSession
        from editorial_assistant.core.extraction import ExtractionContract
        from editorial_assistant.core.data_models import Manuscript
        
        # Test authentication + browser integration
        credentials = {'username': 'test@example.com', 'password': 'test123'}
        auth = ORCIDAuth('SICON', credentials)
        config = BrowserConfig()
        session = BrowserSession(config)
        
        assert auth.validate_credentials() == True
        assert session.config is not None
        print("✅ Authentication + Browser integration working")
        
        # Test browser + extraction integration
        contract = ExtractionContract('SICON', 'SIAM Journal on Control and Optimization')
        contract.begin_extraction()
        
        manuscripts = [
            Manuscript(manuscript_id="SICON-2025-001", title="Control Theory Paper")
        ]
        
        result = contract.create_result(manuscripts)
        
        assert result.status in [
            ExtractionStatus.SUCCESS, 
            ExtractionStatus.PARTIAL_SUCCESS,
            ExtractionStatus.FAILED
        ]
        assert len(result.manuscripts) == 1
        print("✅ Browser + Extraction integration working")
        
        # Test full pipeline compatibility
        assert auth.journal_code == contract.journal_code == 'SICON'
        print("✅ Full pipeline integration working")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        traceback.print_exc()
        return False


def test_error_handling():
    """Test error handling across components."""
    print("\n🛡️  Testing Error Handling...")
    
    try:
        from editorial_assistant.core.authentication import ORCIDAuth
        from editorial_assistant.core.extraction import ExtractionContract, ExtractionStatus
        
        # Test authentication with invalid credentials
        invalid_auth = ORCIDAuth('INVALID', {})
        assert invalid_auth.validate_credentials() == False
        print("✅ Authentication error handling working")
        
        # Test extraction with no data
        contract = ExtractionContract('TEST', 'Test Journal')
        result = contract.create_result([])  # Empty manuscripts
        
        assert result.status == ExtractionStatus.FAILED
        assert result.quality_score.overall_score < 0.5
        print("✅ Extraction error handling working")
        
        # Test quality threshold enforcement
        high_threshold_contract = ExtractionContract(
            'TEST', 'Test Journal', 
            minimum_quality_threshold=0.95
        )
        
        from editorial_assistant.core.data_models import Manuscript
        poor_manuscripts = [Manuscript(manuscript_id="")]  # No ID
        poor_result = high_threshold_contract.create_result(poor_manuscripts)
        
        assert poor_result.quality_score.overall_score < 0.95
        print("✅ Quality threshold enforcement working")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        traceback.print_exc()
        return False


async def main():
    """Run all foundation tests."""
    print("🚀 Phase 1 Foundation Test Suite")
    print("=" * 50)
    
    tests = [
        ("Import Tests", test_imports),
        ("Authentication Tests", test_authentication_providers),
        ("Browser Management Tests", test_browser_configuration),
        ("Extraction Contract Tests", test_extraction_contract),
        ("Async Functionality Tests", test_async_functionality),
        ("Integration Tests", test_integration),
        ("Error Handling Tests", test_error_handling)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📝 Running {test_name}...")
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
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
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Phase 1 Foundation is working correctly!")
        return True
    else:
        print("⚠️  Some tests failed - Phase 1 Foundation needs fixes")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)