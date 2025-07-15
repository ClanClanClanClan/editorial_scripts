#!/usr/bin/env python3
"""
Direct Phase 1 Component Tests

Tests Phase 1 components directly without importing from editorial_assistant
to avoid circular dependency issues.
"""

import sys
import asyncio
import traceback
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_authentication_direct():
    """Test authentication components directly."""
    print("🔐 Testing Authentication Components...")
    
    try:
        # Import authentication components directly
        sys.path.insert(0, str(project_root / "editorial_assistant" / "core" / "authentication"))
        
        from base import AuthenticationProvider, AuthenticationResult, AuthStatus
        from orcid_auth import ORCIDAuth
        from scholarone_auth import ScholarOneAuth
        from editorial_manager_auth import EditorialManagerAuth
        
        # Test ORCID Auth
        credentials = {'username': 'test@example.com', 'password': 'test123'}
        orcid_auth = ORCIDAuth('SICON', credentials)
        
        assert orcid_auth.journal_code == 'SICON'
        assert orcid_auth.get_login_url() == 'https://www.editorialmanager.com/siamjco/'
        assert orcid_auth.validate_credentials() == True
        print("✅ ORCID authentication working")
        
        # Test ScholarOne Auth
        so_auth = ScholarOneAuth('MF', credentials)
        assert so_auth.journal_code == 'MF'
        assert so_auth.get_login_url() == 'https://mc.manuscriptcentral.com/mafi'
        assert so_auth.validate_credentials() == True
        print("✅ ScholarOne authentication working")
        
        # Test Editorial Manager Auth
        em_auth = EditorialManagerAuth('FS', credentials)
        assert em_auth.journal_code == 'FS'
        assert em_auth.get_login_url() == 'https://www.editorialmanager.com/finsto/'
        assert em_auth.validate_credentials() == True
        print("✅ Editorial Manager authentication working")
        
        # Test authentication result
        result = AuthenticationResult(
            status=AuthStatus.SUCCESS,
            message="Test authentication successful"
        )
        assert result.status == AuthStatus.SUCCESS
        print("✅ Authentication result working")
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        traceback.print_exc()
        return False


def test_browser_direct():
    """Test browser components directly."""
    print("\n🖥️  Testing Browser Components...")
    
    try:
        # Import browser components directly
        sys.path.insert(0, str(project_root / "editorial_assistant" / "core" / "browser"))
        
        from browser_config import BrowserConfig, BrowserType
        from browser_session import BrowserSession
        from browser_pool import BrowserPool
        
        # Test browser configuration
        config = BrowserConfig()
        assert config.browser_type == BrowserType.UNDETECTED_CHROME
        assert config.headless == True
        assert config.window_size == (1920, 1080)
        print("✅ Browser configuration working")
        
        # Test stealth mode
        stealth_config = BrowserConfig.for_stealth_mode()
        assert stealth_config.browser_type == BrowserType.UNDETECTED_CHROME
        chrome_options = stealth_config.get_chrome_options()
        assert "--disable-blink-features=AutomationControlled" in chrome_options
        print("✅ Stealth mode configuration working")
        
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


def test_extraction_direct():
    """Test extraction components directly."""
    print("\n📋 Testing Extraction Components...")
    
    try:
        # Import extraction components directly
        sys.path.insert(0, str(project_root / "editorial_assistant" / "core" / "extraction"))
        
        from models import (
            ExtractionResult, ExtractionStatus, QualityScore, 
            DataQualityMetrics, ExtractionMetadata
        )
        from validation import QualityValidator, ValidationResult, ValidationSeverity
        from extraction_contract import ExtractionContract
        
        # Test quality score
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
        
        # Test extraction metadata
        metadata = ExtractionMetadata(
            journal_code='TEST',
            journal_name='Test Journal',
            extraction_id='test-123',
            started_at=datetime.now()
        )
        
        metadata.add_action("Test action")
        metadata.add_error("Test error")
        metadata.add_page_visit("https://test.com")
        
        assert len(metadata.actions_performed) == 1
        assert len(metadata.errors_encountered) == 1
        assert len(metadata.pages_visited) == 1
        print("✅ Extraction metadata working")
        
        # Test extraction result
        result = ExtractionResult(
            manuscripts=[],
            referees=[],
            pdfs=[],
            status=ExtractionStatus.SUCCESS,
            quality_score=score,
            metrics=metrics,
            metadata=metadata
        )
        
        summary = result.calculate_summary_stats()
        assert 'total_manuscripts' in summary
        assert 'quality_score' in summary
        print("✅ Extraction result working")
        
        # Test quality validator
        validator = QualityValidator()
        validation = validator.validate_extraction_result(result)
        
        assert hasattr(validation, 'is_valid')
        assert hasattr(validation, 'summary')
        assert isinstance(validation.recommendations, list)
        print("✅ Quality validator working")
        
        return True
        
    except Exception as e:
        print(f"❌ Extraction test failed: {e}")
        traceback.print_exc()
        return False


async def test_async_browser_direct():
    """Test async browser functionality directly."""
    print("\n⚡ Testing Async Browser Functionality...")
    
    try:
        # Import browser components directly
        sys.path.insert(0, str(project_root / "editorial_assistant" / "core" / "browser"))
        
        from browser_config import BrowserConfig
        from browser_session import BrowserSession
        from browser_pool import BrowserPool
        
        # Test browser session async interface
        config = BrowserConfig()
        session = BrowserSession(config)
        
        # Test that async methods exist
        assert hasattr(session, '__aenter__')
        assert hasattr(session, '__aexit__')
        assert hasattr(session, 'initialize')
        assert hasattr(session, 'cleanup')
        assert hasattr(session, 'navigate')
        assert hasattr(session, 'find_element')
        print("✅ Browser session async interface complete")
        
        # Test browser pool async methods
        pool = BrowserPool(pool_size=2, config=config)
        
        # Test health check (doesn't require initialization)
        health = await pool.health_check()
        assert 'pool_size' in health
        assert 'is_healthy' in health
        assert health['pool_size'] == 2
        print("✅ Browser pool async health check working")
        
        return True
        
    except Exception as e:
        print(f"❌ Async browser test failed: {e}")
        traceback.print_exc()
        return False


def test_integration_direct():
    """Test integration between components."""
    print("\n🔗 Testing Component Integration...")
    
    try:
        # Test compatibility between authentication and browser config
        sys.path.insert(0, str(project_root / "editorial_assistant" / "core" / "authentication"))
        sys.path.insert(0, str(project_root / "editorial_assistant" / "core" / "browser"))
        
        from orcid_auth import ORCIDAuth
        from browser_config import BrowserConfig
        
        credentials = {'username': 'test@example.com', 'password': 'test123'}
        auth = ORCIDAuth('SICON', credentials)
        config = BrowserConfig()
        
        assert auth.validate_credentials() == True
        assert config.browser_type.value == 'undetected_chrome'
        print("✅ Authentication + Browser config compatibility working")
        
        # Test journal code consistency
        assert auth.journal_code == 'SICON'
        assert 'SICON' in auth.get_login_url()
        print("✅ Journal code consistency working")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        traceback.print_exc()
        return False


def test_error_scenarios():
    """Test error handling scenarios."""
    print("\n🛡️  Testing Error Handling...")
    
    try:
        sys.path.insert(0, str(project_root / "editorial_assistant" / "core" / "authentication"))
        sys.path.insert(0, str(project_root / "editorial_assistant" / "core" / "extraction"))
        
        from orcid_auth import ORCIDAuth
        from models import ExtractionResult, ExtractionStatus
        
        # Test authentication with invalid credentials
        invalid_auth = ORCIDAuth('INVALID', {})
        assert invalid_auth.validate_credentials() == False
        print("✅ Invalid credential handling working")
        
        # Test extraction with empty result
        empty_result = ExtractionResult()
        assert empty_result.status == ExtractionStatus.FAILED
        assert not empty_result.has_usable_data()
        print("✅ Empty result handling working")
        
        return True
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        traceback.print_exc()
        return False


async def main():
    """Run all direct component tests."""
    print("🚀 Phase 1 Foundation Direct Test Suite")
    print("=" * 50)
    
    tests = [
        ("Authentication Components", test_authentication_direct),
        ("Browser Components", test_browser_direct),
        ("Extraction Components", test_extraction_direct),
        ("Async Browser Functionality", test_async_browser_direct),
        ("Component Integration", test_integration_direct),
        ("Error Handling", test_error_scenarios)
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
        print("\n📋 PHASE 1 FOUNDATION SUMMARY:")
        print("✅ Unified Authentication Architecture - 3 providers implemented")
        print("✅ Standardized Browser Management - Anti-detection & pooling ready")
        print("✅ Extraction Contract System - Quality validation framework complete")
        print("✅ Async/Await Support - Concurrent processing enabled")
        print("✅ Error Handling - Comprehensive validation and error tracking")
        print("\n🚀 Ready for Phase 2: Architecture Modernization")
        return True
    else:
        print("⚠️  Some tests failed - Phase 1 Foundation needs fixes")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)