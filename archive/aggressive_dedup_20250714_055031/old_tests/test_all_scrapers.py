#!/usr/bin/env python3
"""
Comprehensive test script for all journal scrapers
Tests SICON, SIFIN, MF, and MOR scrapers in headless mode
"""

import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import json

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set credentials
os.environ['ORCID_EMAIL'] = 'dylan.possamai@polytechnique.org'
os.environ['ORCID_PASSWORD'] = 'Hioupy0042%'

# Add MF/MOR credentials if available
# os.environ['MF_USER'] = 'your_username'
# os.environ['MF_PASS'] = 'your_password'
# os.environ['MOR_USER'] = 'your_username'
# os.environ['MOR_PASS'] = 'your_password'
# os.environ['SCHOLARONE_USER'] = 'your_username'
# os.environ['SCHOLARONE_PASS'] = 'your_password'


async def test_scraper(scraper_class, journal_code: str):
    """Test a single scraper"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING {journal_code} SCRAPER")
    print(f"{'='*60}\n")
    
    try:
        # Create scraper
        print(f"📊 Creating {journal_code} scraper...")
        scraper = scraper_class()
        print(f"✅ Scraper created successfully")
        print(f"   Base URL: {scraper.base_url}")
        print(f"   Journal: {scraper.journal_code}")
        
        # Run extraction
        print(f"\n🔄 Running extraction...")
        start_time = datetime.now()
        result = await scraper.run_extraction()
        duration = datetime.now() - start_time
        
        if result.success:
            print(f"\n✅ EXTRACTION SUCCESSFUL!")
            print(f"   Total manuscripts: {result.total_count}")
            print(f"   Extraction time: {duration}")
            
            # Show document statistics
            if result.metadata.get('documents_downloaded'):
                docs = result.metadata['documents_downloaded']
                print(f"\n📎 Document Downloads:")
                print(f"   Manuscripts: {docs.get('manuscripts', 0)}")
                print(f"   Cover letters: {docs.get('cover_letters', 0)}")
                print(f"   Referee reports: {docs.get('referee_reports', 0)}")
            
            # Show manuscript details (first 3)
            if result.manuscripts:
                print(f"\n📄 Sample Manuscripts:")
                for i, ms in enumerate(result.manuscripts[:3], 1):
                    print(f"\n   {i}. {ms.id}")
                    print(f"      Title: {ms.title[:60]}...")
                    print(f"      Status: {ms.status}")
                    
                    # Document info
                    docs = ms.metadata.get('documents', {})
                    if docs:
                        if docs.get('manuscript_pdf_local'):
                            print(f"      PDF: ✓")
                        if docs.get('cover_letter_local'):
                            print(f"      Cover: ✓")
                        if docs.get('referee_reports_local'):
                            print(f"      Reports: {len(docs['referee_reports_local'])}")
                    
                    # Referee info
                    if ms.referees:
                        print(f"      Referees: {len(ms.referees)}")
            
            return True, result
            
        else:
            print(f"\n❌ EXTRACTION FAILED!")
            print(f"   Error: {result.error_message}")
            print(f"   Duration: {duration}")
            return False, result
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False, None


async def test_all_scrapers():
    """Test all journal scrapers"""
    print("🚀 COMPREHENSIVE JOURNAL SCRAPER TEST")
    print("=" * 60)
    print("Testing all scrapers in HEADLESS mode with:")
    print("- Authentication")
    print("- Manuscript extraction")
    print("- Document downloads")
    print("- Metadata storage")
    print("=" * 60)
    
    # Import scrapers
    from src.infrastructure.scrapers.siam_scraper import SIAMScraper
    
    # Test results
    results = {}
    
    # Test SIAM scrapers (SIFIN and SICON)
    for journal_code in ['SIFIN', 'SICON']:
        try:
            scraper_class = lambda: SIAMScraper(journal_code)
            success, result = await test_scraper(scraper_class, journal_code)
            results[journal_code] = {
                'success': success,
                'manuscripts': result.total_count if result else 0,
                'error': result.error_message if result and not success else None
            }
        except Exception as e:
            results[journal_code] = {
                'success': False,
                'manuscripts': 0,
                'error': str(e)
            }
    
    # Test MF scraper if credentials are available
    if os.environ.get('MF_USER') or os.environ.get('SCHOLARONE_USER'):
        try:
            from src.infrastructure.scrapers.mf_scraper_fixed import MFScraperFixed
            success, result = await test_scraper(MFScraperFixed, 'MF')
            results['MF'] = {
                'success': success,
                'manuscripts': result.total_count if result else 0,
                'error': result.error_message if result and not success else None
            }
        except Exception as e:
            results['MF'] = {
                'success': False,
                'manuscripts': 0,
                'error': str(e)
            }
    else:
        print("\n⚠️  Skipping MF scraper - no credentials provided")
        results['MF'] = {'success': None, 'manuscripts': 0, 'error': 'No credentials'}
    
    # Test MOR scraper if credentials are available
    if os.environ.get('MOR_USER') or os.environ.get('MF_USER') or os.environ.get('SCHOLARONE_USER'):
        try:
            from src.infrastructure.scrapers.mor_scraper_fixed import MORScraperFixed
            success, result = await test_scraper(MORScraperFixed, 'MOR')
            results['MOR'] = {
                'success': success,
                'manuscripts': result.total_count if result else 0,
                'error': result.error_message if result and not success else None
            }
        except Exception as e:
            results['MOR'] = {
                'success': False,
                'manuscripts': 0,
                'error': str(e)
            }
    else:
        print("\n⚠️  Skipping MOR scraper - no credentials provided")
        results['MOR'] = {'success': None, 'manuscripts': 0, 'error': 'No credentials'}
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    for journal, result in results.items():
        if result['success'] is True:
            status = f"✅ PASSED ({result['manuscripts']} manuscripts)"
        elif result['success'] is False:
            status = f"❌ FAILED: {result['error']}"
        else:
            status = "⏭️  SKIPPED"
        
        print(f"{journal}: {status}")
    
    # Data storage location
    data_dir = Path.home() / '.editorial_scripts' / 'documents'
    print(f"\n📁 All data stored in: {data_dir}")
    print("   - manuscripts/: Downloaded PDFs")
    print("   - metadata/: JSON metadata files")
    
    # Save test results
    results_file = data_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            'test_date': datetime.now().isoformat(),
            'results': results,
            'data_directory': str(data_dir)
        }, f, indent=2)
    
    print(f"\n💾 Test results saved to: {results_file}")
    
    # Check overall success
    all_passed = all(r['success'] for r in results.values() if r['success'] is not None)
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  Some tests failed or were skipped")


if __name__ == "__main__":
    asyncio.run(test_all_scrapers())