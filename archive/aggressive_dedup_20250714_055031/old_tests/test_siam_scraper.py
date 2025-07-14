#!/usr/bin/env python3
"""
Test script for SIAM scraper implementation
Validates authentication, extraction, and orchestration
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.infrastructure.scrapers.siam_scraper import SIAMScraper
from src.infrastructure.scrapers.siam_orchestrator import SIAMScrapingOrchestrator, extract_all_siam_journals
from src.infrastructure.config import settings


def setup_test_logging():
    """Setup logging for tests"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'siam_scraper_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )


async def test_siam_scraper_single(journal_code: str):
    """Test single SIAM journal scraper"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING SINGLE SIAM SCRAPER: {journal_code}")
    print(f"{'='*60}")
    
    try:
        # Create scraper
        scraper = SIAMScraper(journal_code)
        print(f"✅ Created {journal_code} scraper")
        
        # Test configuration
        config = scraper.config
        print(f"📋 Configuration:")
        print(f"   Base URL: {config.base_url}")
        print(f"   Folder ID: {config.folder_id}")
        print(f"   Max Manuscripts: {config.max_manuscripts}")
        print(f"   Stealth Mode: {config.stealth_mode}")
        
        # Run extraction
        print(f"\n🚀 Starting extraction for {journal_code}...")
        result = await scraper.run_extraction()
        
        # Display results
        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"   Success: {'✅' if result.success else '❌'}")
        print(f"   Manuscripts: {result.total_count}")
        print(f"   Extraction Time: {result.extraction_time}")
        
        if result.error_message:
            print(f"   Error: {result.error_message}")
        
        # Display manuscript details
        if result.manuscripts:
            print(f"\n📄 MANUSCRIPT DETAILS:")
            for i, manuscript in enumerate(result.manuscripts[:3]):  # Show first 3
                print(f"   {i+1}. {manuscript.id}: {manuscript.title[:60]}...")
                print(f"      Referees: {len(manuscript.referees)}")
                print(f"      Documents: {len(manuscript.documents)}")
                print(f"      Status: {manuscript.status.value}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error testing {journal_code} scraper: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_siam_orchestrator():
    """Test SIAM orchestrator with multiple journals"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING SIAM ORCHESTRATOR")
    print(f"{'='*60}")
    
    try:
        # Test sequential extraction
        print("🔄 Testing sequential extraction...")
        orchestrator = SIAMScrapingOrchestrator(['SICON', 'SIFIN'])
        result = await orchestrator.run_sequential_extraction()
        
        print(f"\n📊 ORCHESTRATION RESULTS:")
        print(f"   Overall Success: {'✅' if result.success else '❌'}")
        print(f"   Total Manuscripts: {result.total_manuscripts}")
        print(f"   Total Time: {result.total_time}")
        print(f"   Journals Attempted: {len(result.results_by_journal)}")
        
        # Journal-specific results
        print(f"\n📋 JOURNAL RESULTS:")
        for journal_code, journal_result in result.results_by_journal.items():
            status = "✅" if journal_result.success else "❌"
            print(f"   {journal_code}: {status} - {journal_result.total_count} manuscripts")
            if journal_result.error_message:
                print(f"      Error: {journal_result.error_message}")
        
        # Data validation
        print(f"\n🔍 Running data validation...")
        validation_results = await orchestrator.validate_extraction_data(result)
        
        print(f"\n✅ VALIDATION RESULTS:")
        for journal_code, validation in validation_results.items():
            if validation.get('validated'):
                print(f"   {journal_code}: ✅ VALID (score: {validation.get('score', 0):.2f})")
            else:
                print(f"   {journal_code}: ❌ INVALID ({validation.get('reason', 'Unknown')})")
                
                if 'data_quality_issues' in validation:
                    for issue in validation['data_quality_issues']:
                        print(f"      - {issue}")
        
        # Export summary
        summary = orchestrator.export_results_summary(result)
        print(f"\n📤 Exported summary with {len(summary)} sections")
        
        return result
        
    except Exception as e:
        print(f"❌ Error testing orchestrator: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_parallel_extraction():
    """Test parallel extraction using convenience function"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING PARALLEL EXTRACTION")
    print(f"{'='*60}")
    
    try:
        print("⚡ Running parallel extraction for all SIAM journals...")
        result = await extract_all_siam_journals(parallel=True, max_concurrent=2)
        
        print(f"\n📊 PARALLEL EXTRACTION RESULTS:")
        print(f"   Success: {'✅' if result.success else '❌'}")
        print(f"   Total Manuscripts: {result.total_manuscripts}")
        print(f"   Total Time: {result.total_time}")
        print(f"   Parallel Execution: {result.metadata.get('parallel_execution', False)}")
        
        # Performance comparison
        avg_time_per_journal = result.total_time.total_seconds() / len(result.results_by_journal)
        print(f"   Avg Time per Journal: {avg_time_per_journal:.1f}s")
        
        return result
        
    except Exception as e:
        print(f"❌ Error testing parallel extraction: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_authentication_only():
    """Test authentication without full extraction"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING AUTHENTICATION ONLY")
    print(f"{'='*60}")
    
    try:
        # Test SICON authentication
        print("🔐 Testing SICON authentication...")
        sicon_scraper = SIAMScraper('SICON')
        
        browser = await sicon_scraper.create_browser()
        context = await sicon_scraper.setup_browser_context(browser)
        page = await context.new_page()
        
        auth_success = await sicon_scraper.authenticate(page)
        print(f"   SICON Auth: {'✅ SUCCESS' if auth_success else '❌ FAILED'}")
        
        await context.close()
        await browser.close()
        
        # Test SIFIN authentication
        print("🔐 Testing SIFIN authentication...")
        sifin_scraper = SIAMScraper('SIFIN')
        
        browser = await sifin_scraper.create_browser()
        context = await sifin_scraper.setup_browser_context(browser)
        page = await context.new_page()
        
        auth_success = await sifin_scraper.authenticate(page)
        print(f"   SIFIN Auth: {'✅ SUCCESS' if auth_success else '❌ FAILED'}")
        
        await context.close()
        await browser.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing authentication: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_configuration():
    """Check if required configuration is available"""
    print(f"\n{'='*60}")
    print(f"🔧 CHECKING CONFIGURATION")
    print(f"{'='*60}")
    
    config_status = {}
    
    # Check ORCID credentials
    if hasattr(settings, 'orcid_email') and settings.orcid_email:
        print("✅ ORCID email configured")
        config_status['orcid_email'] = True
    else:
        print("❌ ORCID email not configured")
        config_status['orcid_email'] = False
    
    if hasattr(settings, 'orcid_password') and settings.orcid_password:
        print("✅ ORCID password configured")
        config_status['orcid_password'] = True
    else:
        print("❌ ORCID password not configured")
        config_status['orcid_password'] = False
    
    # Check browser dependencies
    try:
        from playwright.async_api import async_playwright
        print("✅ Playwright available")
        config_status['playwright'] = True
    except ImportError:
        print("❌ Playwright not available")
        config_status['playwright'] = False
    
    all_good = all(config_status.values())
    print(f"\n🎯 Configuration Status: {'✅ READY' if all_good else '❌ ISSUES FOUND'}")
    
    if not all_good:
        print("\n⚠️ Configuration Issues:")
        for key, status in config_status.items():
            if not status:
                print(f"   - {key} needs attention")
        
        print("\n📋 Setup Instructions:")
        if not config_status.get('orcid_email') or not config_status.get('orcid_password'):
            print("   1. Set ORCID_EMAIL and ORCID_PASSWORD environment variables")
            print("   2. Or update src/infrastructure/config.py with credentials")
        
        if not config_status.get('playwright'):
            print("   3. Install Playwright: pip install playwright")
            print("   4. Install browsers: playwright install")
    
    return all_good


async def run_comprehensive_test():
    """Run comprehensive test suite"""
    print(f"🧪 SIAM SCRAPER COMPREHENSIVE TEST SUITE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    # Check configuration first
    config_ok = check_configuration()
    if not config_ok:
        print("\n❌ Configuration issues found. Please fix before running tests.")
        return False
    
    test_results = {}
    
    # Test 1: Authentication only
    print(f"\n🔍 TEST 1: Authentication Testing")
    auth_result = await test_authentication_only()
    test_results['authentication'] = auth_result
    
    if not auth_result:
        print("⚠️ Authentication failed, skipping extraction tests")
        return False
    
    # Test 2: Single scraper (SICON first as it's more reliable)
    print(f"\n🔍 TEST 2: Single Scraper (SICON)")
    sicon_result = await test_siam_scraper_single('SICON')
    test_results['sicon_extraction'] = sicon_result is not None and sicon_result.success
    
    # Test 3: Single scraper (SIFIN)
    print(f"\n🔍 TEST 3: Single Scraper (SIFIN)")
    sifin_result = await test_siam_scraper_single('SIFIN')
    test_results['sifin_extraction'] = sifin_result is not None and sifin_result.success
    
    # Test 4: Orchestrator (sequential)
    print(f"\n🔍 TEST 4: Orchestrator (Sequential)")
    orchestrator_result = await test_siam_orchestrator()
    test_results['orchestrator'] = orchestrator_result is not None and orchestrator_result.success
    
    # Test 5: Parallel extraction
    print(f"\n🔍 TEST 5: Parallel Extraction")
    parallel_result = await test_parallel_extraction()
    test_results['parallel_extraction'] = parallel_result is not None and parallel_result.success
    
    # Final summary
    print(f"\n{'='*80}")
    print(f"🎯 COMPREHENSIVE TEST SUMMARY")
    print(f"{'='*80}")
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    print(f"\n📋 Test Results:")
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    overall_success = passed_tests == total_tests
    print(f"\n🏆 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    return overall_success


if __name__ == "__main__":
    # Setup logging
    setup_test_logging()
    
    # Run tests
    try:
        success = asyncio.run(run_comprehensive_test())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)