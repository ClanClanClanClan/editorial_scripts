#!/usr/bin/env python3
"""
Final test of 1Password integration
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_1password_integration():
    """Test 1Password credential retrieval"""
    
    print("🔧 TESTING 1PASSWORD INTEGRATION")
    print("=" * 40)
    
    try:
        # Import credential manager
        from src.core.credential_manager import get_credential_manager
        
        print("✅ Credential manager imported successfully")
        
        # Get manager instance
        cred_manager = get_credential_manager()
        print("✅ Credential manager instance created")
        
        # Test SICON credentials
        print("\n🔍 Testing SICON credentials...")
        sicon_creds = cred_manager.get_credentials('SICON')
        
        if sicon_creds:
            print(f"✅ SICON credentials found!")
            print(f"   Username: {sicon_creds.get('username', 'N/A')[:10]}...")
            print(f"   Password: {'*' * len(sicon_creds.get('password', ''))}")
            print(f"   Email: {sicon_creds.get('email', 'N/A')[:10]}...")
        else:
            print("❌ SICON credentials not found")
        
        # Test SIFIN credentials  
        print("\n🔍 Testing SIFIN credentials...")
        sifin_creds = cred_manager.get_credentials('SIFIN')
        
        if sifin_creds:
            print(f"✅ SIFIN credentials found!")
            print(f"   Username: {sifin_creds.get('username', 'N/A')[:10]}...")
            print(f"   Password: {'*' * len(sifin_creds.get('password', ''))}")
        else:
            print("❌ SIFIN credentials not found")
        
        # Test direct 1Password method
        print("\n🔍 Testing direct 1Password method...")
        orcid_creds = cred_manager._get_1password_credentials('ORCID')
        
        if orcid_creds:
            print(f"✅ Direct 1Password ORCID retrieval working!")
            print(f"   Username: {orcid_creds.get('username', 'N/A')[:10]}...")
        else:
            print("❌ Direct 1Password method failed")
        
        # Test available journals
        print("\n📋 Available journals:")
        available = cred_manager.list_available_journals()
        for journal in available:
            print(f"  ✅ {journal}")
        
        if not available:
            print("  ❌ No journals with credentials found")
        
        return len(available) > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_1password_integration()
    
    if success:
        print("\n🎉 1PASSWORD INTEGRATION WORKING!")
        print("\n📋 Next steps:")
        print("1. Test SICON extraction: python3 run_unified_with_1password.py --journal SICON")
        print("2. Check output in: output/sicon/")
    else:
        print("\n❌ 1Password integration needs more work")
        print("\nTroubleshooting:")
        print("1. Ensure 1Password CLI is signed in: op signin")
        print("2. Check ORCID item exists: op item list | grep -i orcid")
        print("3. Verify credentials: op item get ORCID")