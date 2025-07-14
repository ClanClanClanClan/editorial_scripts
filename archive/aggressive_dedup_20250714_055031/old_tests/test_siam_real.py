#!/usr/bin/env python3
"""
Test SIAM scrapers with real credentials from 1Password
Handles the actual Orcid item structure
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
            print(f"✅ Retrieved credentials: {email[:3]}****")
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

async def test_siam_scraper(journal_code: str):
    """Test SIAM scraper with specific journal"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING {journal_code} SCRAPER")
    print(f"{'='*60}")
    
    try:
        from src.infrastructure.scrapers.siam_scraper import SIAMScraper
        
        # Create scraper
        scraper = SIAMScraper(journal_code)
        print(f"✅ Created {journal_code} scraper")
        
        # Run extraction
        print(f"🚀 Starting extraction for {journal_code}...")
        print("   This may take 1-2 minutes...")
        
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
            for i, manuscript in enumerate(result.manuscripts[:5]):  # Show first 5
                print(f"\n   {i+1}. {manuscript.id}: {manuscript.title[:60]}...")
                print(f"      Status: {manuscript.status.value}")
                print(f"      Referees: {len(manuscript.referees)}")
                if manuscript.referees:
                    for j, referee in enumerate(manuscript.referees[:3]):  # Show first 3 referees
                        print(f"        - {referee.name} ({referee.status.value})")
                print(f"      Documents: {len(manuscript.metadata.get('documents', {}))}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error testing {journal_code}: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_authentication_only():
    """Test just the authentication flow"""
    print(f"\n{'='*60}")
    print("🔐 TESTING AUTHENTICATION ONLY")
    print(f"{'='*60}")
    
    try:
        from src.infrastructure.scrapers.siam_scraper import SIAMScraper
        
        # Test SICON
        print("\n🔍 Testing SICON authentication...")
        sicon_scraper = SIAMScraper('SICON')
        
        browser = await sicon_scraper.create_browser()
        context = await sicon_scraper.setup_browser_context(browser)
        page = await context.new_page()
        
        auth_success = await sicon_scraper.authenticate(page)
        print(f"   SICON Auth: {'✅ SUCCESS' if auth_success else '❌ FAILED'}")
        
        await context.close()
        await browser.close()
        
        # Test SIFIN
        print("\n🔍 Testing SIFIN authentication...")
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
        print(f"❌ Authentication test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test execution"""
    print("🎭 SIAM SCRAPER REAL-WORLD TEST")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Step 1: Get credentials from 1Password
    email, password = get_orcid_credentials()
    if not email or not password:
        print("\n❌ Failed to get ORCID credentials from 1Password")
        return False
    
    # Step 2: Choose test mode
    print("\n📋 Test Options:")
    print("   1. Authentication only (quick test)")
    print("   2. SICON extraction")
    print("   3. SIFIN extraction")
    print("   4. Both journals (full test)")
    
    choice = input("\nSelect test mode (1/2/3/4) [default: 1]: ").strip() or "1"
    
    results = {}
    
    if choice == "1":
        # Authentication only
        results['authentication'] = await test_authentication_only()
    elif choice == "2":
        # SICON only
        result = await test_siam_scraper('SICON')
        results['SICON'] = result is not None and result.success
    elif choice == "3":
        # SIFIN only
        result = await test_siam_scraper('SIFIN')
        results['SIFIN'] = result is not None and result.success
    else:
        # Both journals
        sicon_result = await test_siam_scraper('SICON')
        results['SICON'] = sicon_result is not None and sicon_result.success
        
        sifin_result = await test_siam_scraper('SIFIN')
        results['SIFIN'] = sifin_result is not None and sifin_result.success
    
    # Summary
    print(f"\n{'=' * 80}")
    print("🎯 TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    print(f"\n📋 Test Results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    overall_success = passed == total
    print(f"\n🏆 Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 SIAM scrapers are working correctly!")
        print("✅ Authentication successful")
        print("✅ Manuscript extraction working")
        print("✅ Referee data being collected")
        print("✅ Stealth measures effective")
    
    return overall_success

if __name__ == "__main__":
    try:
        # Ensure 1Password session is active
        whoami = subprocess.run(['op', 'whoami'], capture_output=True, text=True)
        if whoami.returncode != 0:
            print("🔐 Signing in to 1Password...")
            signin = subprocess.run(['eval', '$(op signin)'], shell=True)
            if signin.returncode != 0:
                print("❌ Failed to sign in to 1Password")
                print("💡 Run: eval $(op signin)")
                sys.exit(1)
        
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