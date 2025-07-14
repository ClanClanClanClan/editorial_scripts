#!/usr/bin/env python3
"""
Automated test of SIAM scrapers with real credentials
No user input required - runs authentication test by default
"""

import asyncio
import sys
import os
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Add src and core to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def get_orcid_credentials():
    """Get ORCID credentials directly from 1Password"""
    print("🔐 Getting ORCID credentials from 1Password...")
    
    try:
        # Get userId field
        userId_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=userId'], 
                                   capture_output=True, text=True)
        if userId_cmd.returncode != 0:
            print(f"❌ Failed to get userId: {userId_cmd.stderr}")
            return None, None
        
        # Get password field
        password_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=password'], 
                                     capture_output=True, text=True)
        if password_cmd.returncode != 0:
            print(f"❌ Failed to get password: {password_cmd.stderr}")
            return None, None
        
        email = userId_cmd.stdout.strip()
        password = password_cmd.stdout.strip()
        
        if email and password:
            print(f"✅ Retrieved credentials: {email[:3]}****@****.***")
            # Set environment variables for the scraper
            os.environ['ORCID_EMAIL'] = email
            os.environ['ORCID_PASSWORD'] = password
            return email, password
        else:
            print("❌ Empty credentials retrieved")
            return None, None
            
    except Exception as e:
        print(f"❌ Error getting credentials: {e}")
        return None, None

async def test_authentication():
    """Test authentication for both journals"""
    print(f"\n{'='*60}")
    print("🔐 TESTING AUTHENTICATION")
    print(f"{'='*60}")
    
    results = {}
    
    try:
        from src.infrastructure.scrapers.siam_scraper import SIAMScraper
        
        # Test SICON
        print("\n🔍 Testing SICON authentication...")
        try:
            sicon_scraper = SIAMScraper('SICON')
            print("   ✅ SICON scraper created")
            
            browser = await sicon_scraper.create_browser()
            print("   ✅ Browser created")
            
            context = await sicon_scraper.setup_browser_context(browser)
            print("   ✅ Stealth context configured")
            
            page = await context.new_page()
            print("   ✅ Page created")
            
            print("   🔄 Attempting authentication...")
            auth_success = await sicon_scraper.authenticate(page)
            
            if auth_success:
                print("   ✅ SICON Authentication: SUCCESS")
                # Try to get manuscript count
                try:
                    print("   🔄 Checking manuscripts...")
                    await sicon_scraper._navigate_to_manuscripts(page)
                    print("   ✅ Successfully navigated to manuscripts")
                except Exception as e:
                    print(f"   ⚠️ Could not navigate to manuscripts: {e}")
            else:
                print("   ❌ SICON Authentication: FAILED")
            
            results['SICON'] = auth_success
            
            await context.close()
            await browser.close()
            
        except Exception as e:
            print(f"   ❌ SICON test failed: {e}")
            results['SICON'] = False
        
        # Test SIFIN
        print("\n🔍 Testing SIFIN authentication...")
        try:
            sifin_scraper = SIAMScraper('SIFIN')
            print("   ✅ SIFIN scraper created")
            
            browser = await sifin_scraper.create_browser()
            print("   ✅ Browser created")
            
            context = await sifin_scraper.setup_browser_context(browser)
            print("   ✅ Stealth context configured")
            
            page = await context.new_page()
            print("   ✅ Page created")
            
            print("   🔄 Attempting authentication...")
            auth_success = await sifin_scraper.authenticate(page)
            
            if auth_success:
                print("   ✅ SIFIN Authentication: SUCCESS")
                # Check if we can see manuscripts
                try:
                    content = await page.content()
                    if 'manuscript' in content.lower() or 'submission' in content.lower():
                        print("   ✅ Manuscripts visible on dashboard")
                except:
                    pass
            else:
                print("   ❌ SIFIN Authentication: FAILED")
            
            results['SIFIN'] = auth_success
            
            await context.close()
            await browser.close()
            
        except Exception as e:
            print(f"   ❌ SIFIN test failed: {e}")
            results['SIFIN'] = False
        
        return results
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        import traceback
        traceback.print_exc()
        return {'SICON': False, 'SIFIN': False}

async def test_quick_extraction():
    """Test quick extraction (first manuscript only)"""
    print(f"\n{'='*60}")
    print("🚀 TESTING QUICK EXTRACTION")
    print(f"{'='*60}")
    
    try:
        from src.infrastructure.scrapers.siam_scraper import SIAMScraper
        
        # Test SICON quick extraction
        print("\n📄 Testing SICON manuscript extraction...")
        sicon_scraper = SIAMScraper('SICON')
        sicon_scraper.config.max_manuscripts = 1  # Only get first manuscript
        
        browser = await sicon_scraper.create_browser()
        context = await sicon_scraper.setup_browser_context(browser)
        page = await context.new_page()
        
        if await sicon_scraper.authenticate(page):
            print("   ✅ Authenticated")
            try:
                manuscripts = await sicon_scraper.extract_manuscripts(page)
                if manuscripts:
                    print(f"   ✅ Extracted {len(manuscripts)} manuscript(s)")
                    ms = manuscripts[0]
                    print(f"      ID: {ms.id}")
                    print(f"      Title: {ms.title[:60]}...")
                    print(f"      Referees: {len(ms.referees)}")
                else:
                    print("   ⚠️ No manuscripts found")
            except Exception as e:
                print(f"   ❌ Extraction failed: {e}")
        
        await context.close()
        await browser.close()
        
    except Exception as e:
        print(f"❌ Quick extraction test failed: {e}")

async def main():
    """Main test execution"""
    print("🎭 SIAM SCRAPER AUTOMATED TEST")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Get credentials from 1Password
    email, password = get_orcid_credentials()
    if not email or not password:
        print("\n❌ Failed to get ORCID credentials from 1Password")
        return False
    
    # Run authentication tests
    auth_results = await test_authentication()
    
    # If authentication works, try quick extraction
    if any(auth_results.values()):
        await test_quick_extraction()
    
    # Summary
    print(f"\n{'=' * 80}")
    print("🎯 TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for result in auth_results.values() if result)
    total = len(auth_results)
    
    print(f"Authentication Tests Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    print(f"\n📋 Results:")
    for journal, result in auth_results.items():
        status = "✅ WORKING" if result else "❌ FAILED"
        print(f"   {journal}: {status}")
    
    if passed == total:
        print("\n🎉 ALL SIAM SCRAPERS ARE WORKING!")
        print("✅ Authentication successful for both journals")
        print("✅ Stealth measures effective")
        print("✅ Ready for full extraction")
        print("\n🚀 To run full extraction:")
        print("   python test_siam_scraper.py")
    elif passed > 0:
        print(f"\n⚠️ {passed}/{total} scrapers working")
        print("Check the logs above for specific issues")
    else:
        print("\n❌ No scrapers working")
        print("Check ORCID credentials and network connectivity")
    
    return passed > 0

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)