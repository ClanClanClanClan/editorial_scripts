#!/usr/bin/env python3
"""
Test 1Password integration with SIAM scraper
Verifies credential retrieval from 1Password CLI
"""

import sys
import subprocess
from pathlib import Path

# Add src and core to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_1password_cli():
    """Test if 1Password CLI is available and configured"""
    print("🔐 TESTING 1PASSWORD INTEGRATION")
    print("=" * 60)
    
    # Test 1: Check if op CLI is installed
    print("\n🔍 Checking 1Password CLI installation...")
    try:
        result = subprocess.run(['op', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ 1Password CLI installed: {result.stdout.strip()}")
        else:
            print("❌ 1Password CLI not found")
            return False
    except FileNotFoundError:
        print("❌ 1Password CLI not installed")
        print("💡 Install from: https://1password.com/downloads/command-line/")
        return False
    
    # Test 2: Check if signed in
    print("\n🔍 Checking 1Password session...")
    try:
        result = subprocess.run(['op', 'whoami'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Signed in as: {result.stdout.strip()}")
        else:
            print("❌ Not signed in to 1Password")
            print("💡 Run: eval $(op signin)")
            return False
    except Exception as e:
        print(f"❌ Error checking session: {e}")
        return False
    
    return True

def test_credential_manager():
    """Test credential manager with 1Password integration"""
    print("\n🔍 Testing Credential Manager...")
    
    try:
        from core.credential_manager import get_credential_manager
        
        # Create credential manager
        cred_manager = get_credential_manager()
        print("✅ Credential manager initialized")
        
        # Test ORCID credentials
        print("\n🔍 Testing ORCID credential retrieval...")
        orcid_creds = cred_manager.get_journal_credentials('ORCID')
        
        if orcid_creds.get('email') and orcid_creds.get('password'):
            print("✅ ORCID credentials retrieved successfully")
            print(f"   Email: {orcid_creds['email'][:3]}****@****.***")
            print(f"   Password: {'*' * 8}")
            return True
        else:
            print("❌ ORCID credentials not found in 1Password")
            print("💡 Make sure ORCID item exists in 1Password with fields:")
            print("   - email: your ORCID email")
            print("   - password: your ORCID password")
            return False
            
    except Exception as e:
        print(f"❌ Error testing credential manager: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_siam_scraper_credentials():
    """Test SIAM scraper credential integration"""
    print("\n🔍 Testing SIAM Scraper Credential Integration...")
    
    try:
        from src.infrastructure.scrapers.siam_scraper import SIAMScraper
        from core.credential_manager import get_credential_manager
        
        # Create scraper
        scraper = SIAMScraper('SICON')
        print("✅ SIAM scraper created")
        
        # Test credential retrieval
        cred_manager = get_credential_manager()
        orcid_creds = cred_manager.get_journal_credentials('ORCID')
        
        if orcid_creds.get('email') and orcid_creds.get('password'):
            print("✅ SIAM scraper can access ORCID credentials from 1Password")
            return True
        else:
            print("⚠️ SIAM scraper will fall back to environment variables")
            return False
            
    except Exception as e:
        print(f"❌ Error testing SIAM scraper: {e}")
        return False

def run_tests():
    """Run all 1Password integration tests"""
    print("🚀 1PASSWORD INTEGRATION TEST SUITE")
    print(f"=" * 80)
    
    results = {}
    
    # Test 1: 1Password CLI
    if test_1password_cli():
        results['1password_cli'] = True
        
        # Test 2: Credential Manager
        results['credential_manager'] = test_credential_manager()
        
        # Test 3: SIAM Scraper Integration
        results['siam_integration'] = test_siam_scraper_credentials()
    else:
        results['1password_cli'] = False
        results['credential_manager'] = False
        results['siam_integration'] = False
    
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
    
    if passed == total:
        print(f"\n🎉 ALL TESTS PASSED!")
        print("✅ 1Password integration is working correctly")
        print("🚀 Ready to run SIAM scraper with credentials from 1Password")
    else:
        print(f"\n⚠️ Some tests failed")
        print("\n📋 Setup Instructions:")
        print("1. Install 1Password CLI: https://1password.com/downloads/command-line/")
        print("2. Sign in: eval $(op signin)")
        print("3. Create ORCID item in 1Password with fields:")
        print("   - email: your ORCID email")
        print("   - password: your ORCID password")
        print("4. Run this test again")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = run_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)