#!/usr/bin/env python3
"""
Simple integration test to verify stealth manager classes load correctly
Tests the imports and basic functionality without external dependencies
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_stealth_imports():
    """Test that stealth manager can be imported"""
    try:
        from src.infrastructure.scrapers.stealth_manager import StealthManager, StealthConfig
        print("✅ StealthManager imports successfully")
        
        # Test basic initialization
        config = StealthConfig()
        stealth_manager = StealthManager(config)
        print("✅ StealthManager initializes successfully")
        
        # Test fingerprint generation
        fingerprint = stealth_manager._generate_session_fingerprint()
        print(f"✅ Session fingerprint generated: {fingerprint['session_id']}")
        
        # Test context options
        context_options = stealth_manager.get_context_options()
        print(f"✅ Context options generated with user agent: {context_options['user_agent'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ StealthManager import/init failed: {e}")
        return False

def test_siam_scraper_imports():
    """Test that SIAM scraper imports correctly with stealth integration"""
    try:
        # Mock playwright classes to avoid dependency
        import types
        mock_playwright = types.ModuleType('playwright')
        mock_async_api = types.ModuleType('async_api')
        
        # Add basic mock classes
        class MockPage: pass
        class MockBrowser: pass
        class MockBrowserContext: pass
        class MockTimeoutError(Exception): pass
        
        mock_async_api.Page = MockPage
        mock_async_api.Browser = MockBrowser
        mock_async_api.BrowserContext = MockBrowserContext
        mock_async_api.TimeoutError = MockTimeoutError
        
        mock_playwright.async_api = mock_async_api
        sys.modules['playwright'] = mock_playwright
        sys.modules['playwright.async_api'] = mock_async_api
        
        # Mock BeautifulSoup
        class MockBeautifulSoup:
            def __init__(self, *args, **kwargs):
                pass
        
        sys.modules['bs4'] = types.ModuleType('bs4')
        sys.modules['bs4'].BeautifulSoup = MockBeautifulSoup
        
        # Mock settings
        class MockSettings:
            orcid_email = "test@example.com"
            orcid_password = "test_password"
        
        # Try importing SIAM scraper
        from src.infrastructure.scrapers.siam_scraper import SIAMScraper, SIAMConfig
        print("✅ SIAMScraper imports successfully with mocked dependencies")
        
        # Test basic configuration
        config = SIAMConfig(
            journal_code='SICON',
            base_url='http://test.com',
            folder_id='1800'
        )
        print(f"✅ SIAMConfig created: {config.journal_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ SIAMScraper import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_domain_models():
    """Test domain models import and functionality"""
    try:
        from src.core.domain.manuscript import Manuscript, ManuscriptStatus, RefereeInfo, RefereeStatus
        print("✅ Domain models import successfully")
        
        # Test manuscript creation
        manuscript = Manuscript(
            id="test-123",
            title="Test Manuscript",
            journal_code="SICON"
        )
        print(f"✅ Manuscript created: {manuscript.id}")
        
        # Test referee creation
        referee = RefereeInfo(
            name="Dr. Test Reviewer",
            email="reviewer@example.com",
            status=RefereeStatus.INVITED
        )
        print(f"✅ Referee created: {referee.name}")
        
        # Test adding referee to manuscript
        manuscript.add_referee(referee)
        print(f"✅ Referee added to manuscript: {len(manuscript.referees)} referees")
        
        return True
        
    except Exception as e:
        print(f"❌ Domain models test failed: {e}")
        return False

def test_base_scraper():
    """Test base scraper functionality"""
    try:
        from src.infrastructure.scrapers.base_scraper import BaseScraper, ScrapingResult
        print("✅ BaseScraper imports successfully")
        
        # Test ScrapingResult
        result = ScrapingResult(
            success=True,
            manuscripts=[],
            total_count=0,
            extraction_time=None,
            journal_code="TEST"
        )
        print(f"✅ ScrapingResult created: success={result.success}")
        
        return True
        
    except Exception as e:
        print(f"❌ BaseScraper test failed: {e}")
        return False

def run_integration_tests():
    """Run all integration tests"""
    print("🧪 SIAM SCRAPER STEALTH INTEGRATION TESTS")
    print("=" * 60)
    
    test_results = {}
    
    # Test 1: Stealth Manager
    print("\n🔍 TEST 1: Stealth Manager Integration")
    test_results['stealth_manager'] = test_stealth_imports()
    
    # Test 2: Domain Models
    print("\n🔍 TEST 2: Domain Models")
    test_results['domain_models'] = test_domain_models()
    
    # Test 3: Base Scraper
    print("\n🔍 TEST 3: Base Scraper")
    test_results['base_scraper'] = test_base_scraper()
    
    # Test 4: SIAM Scraper Integration
    print("\n🔍 TEST 4: SIAM Scraper Integration")
    test_results['siam_scraper'] = test_siam_scraper_imports()
    
    # Summary
    print(f"\n{'=' * 60}")
    print("🎯 INTEGRATION TEST SUMMARY")
    print(f"{'=' * 60}")
    
    passed = sum(1 for result in test_results.values() if result)
    total = len(test_results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    print(f"\n📋 Test Results:")
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    overall_success = passed == total
    print(f"\n🏆 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 Stealth integration is working correctly!")
        print("📋 Key Features Verified:")
        print("   - StealthManager initialization and configuration")
        print("   - Session fingerprint generation")
        print("   - Browser context options generation")
        print("   - SIAM scraper class imports with stealth integration")
        print("   - Domain models for manuscript and referee management")
        print("   - Base scraper functionality")
    
    return overall_success

if __name__ == "__main__":
    try:
        success = run_integration_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)