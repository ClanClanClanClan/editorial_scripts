#!/usr/bin/env python3
"""
Test complete SIAM scraping functionality - authentication + manuscript extraction
"""

import asyncio
import os
import subprocess
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.scrapers.siam_scraper import SIAMScraper
from playwright.async_api import async_playwright

async def test_full_siam_scraping():
    """Test complete SIAM scraping workflow"""
    print("🧪 TESTING COMPLETE SIAM SCRAPING FUNCTIONALITY")
    print("=" * 70)
    
    # Check for environment variables first (automation)
    if os.environ.get('ORCID_EMAIL') and os.environ.get('ORCID_PASSWORD'):
        print(f"✅ Using environment credentials: {os.environ.get('ORCID_EMAIL')[:3]}****")
    else:
        # Try 1Password with short timeout
        try:
            userId_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=userId'], 
                                       capture_output=True, text=True, timeout=3)
            password_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=password'], 
                                         capture_output=True, text=True, timeout=3)
            
            if userId_cmd.returncode == 0 and password_cmd.returncode == 0:
                os.environ['ORCID_EMAIL'] = userId_cmd.stdout.strip()
                os.environ['ORCID_PASSWORD'] = password_cmd.stdout.strip()
                print(f"✅ Got 1Password credentials: {userId_cmd.stdout.strip()[:3]}****")
            else:
                print("❌ 1Password commands failed - need credentials for testing")
                print("💡 To test scraping functionality:")
                print("   export ORCID_EMAIL='your.email@domain.com'")
                print("   export ORCID_PASSWORD='your_password'")
                return False
        except Exception as e:
            print(f"❌ 1Password timeout: {e}")
            print("💡 To test scraping functionality:")
            print("   export ORCID_EMAIL='your.email@domain.com'")  
            print("   export ORCID_PASSWORD='your_password'")
            return False
    
    # Test both SICON and SIFIN
    journals = ['SICON', 'SIFIN']
    results = {}
    
    for journal in journals:
        print(f"\n📊 TESTING {journal} SCRAPER")
        print("=" * 50)
        
        try:
            # Create scraper
            scraper = SIAMScraper(journal)
            print(f"✅ Created {journal} scraper")
            
            # Run complete extraction
            print(f"🔄 Running complete {journal} extraction...")
            result = await scraper.run_extraction()
            
            if result.success:
                print(f"🎉 {journal} EXTRACTION SUCCESSFUL!")
                print(f"   📄 Manuscripts found: {result.total_count}")
                print(f"   ⏱️  Extraction time: {result.extraction_time}")
                print(f"   🔧 Scraper version: {result.metadata.get('scraper_version', 'Unknown')}")
                
                # Display manuscript details
                if result.manuscripts:
                    print(f"\n📋 {journal} MANUSCRIPT DETAILS:")
                    for i, ms in enumerate(result.manuscripts[:3], 1):  # Show first 3
                        print(f"   {i}. ID: {ms.id}")
                        print(f"      Title: {ms.title[:60]}...")
                        print(f"      Status: {ms.status}")
                        print(f"      Referees: {len(ms.referees)}")
                        print(f"      Editor: {ms.associate_editor}")
                        print()
                
                results[journal] = {
                    'success': True,
                    'manuscript_count': result.total_count,
                    'extraction_time': str(result.extraction_time),
                    'manuscripts': result.manuscripts
                }
            else:
                print(f"❌ {journal} EXTRACTION FAILED!")
                print(f"   Error: {result.error_message}")
                results[journal] = {
                    'success': False,
                    'error': result.error_message
                }
                
        except Exception as e:
            print(f"❌ {journal} TEST ERROR: {e}")
            results[journal] = {
                'success': False,
                'error': str(e)
            }
    
    # Final summary
    print("\n" + "=" * 70)
    print("📊 FINAL SCRAPING TEST RESULTS")
    print("=" * 70)
    
    total_success = 0
    total_manuscripts = 0
    
    for journal, result in results.items():
        if result['success']:
            print(f"✅ {journal}: SUCCESS - {result['manuscript_count']} manuscripts")
            total_success += 1
            total_manuscripts += result['manuscript_count']
        else:
            print(f"❌ {journal}: FAILED - {result['error']}")
    
    print(f"\n🎯 SUMMARY:")
    print(f"   Successful scrapers: {total_success}/2")
    print(f"   Total manuscripts: {total_manuscripts}")
    
    if total_success == 2:
        print("\n🎉 ALL SIAM SCRAPERS WORKING PERFECTLY!")
        print("✅ Authentication working")
        print("✅ Modal handling working")
        print("✅ Manuscript extraction working")
        print("✅ Data parsing working")
        print("✅ Ready for production use")
        return True
    else:
        print(f"\n⚠️ {2 - total_success} scraper(s) need attention")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_full_siam_scraping())
    sys.exit(0 if success else 1)