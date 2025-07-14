#!/usr/bin/env python3
"""
Test integration of secure credential manager with the main system
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

def test_secure_integration():
    """Test secure credential manager integration"""
    
    print("🔐 TESTING SECURE CREDENTIAL INTEGRATION")
    print("=" * 50)
    
    try:
        # Import credential manager
        from src.core.credential_manager import get_credential_manager
        
        print("✅ Credential manager imported successfully")
        
        # Get manager instance
        cred_manager = get_credential_manager()
        print("✅ Credential manager instance created")
        
        # Test SICON credentials (should use secure storage)
        print("\n🔍 Testing SICON credentials via secure storage...")
        sicon_creds = cred_manager.get_credentials('SICON')
        
        if sicon_creds:
            print(f"✅ SICON credentials found!")
            print(f"   Username: {sicon_creds.get('username', 'N/A')[:10]}...")
            print(f"   Email: {sicon_creds.get('email', 'N/A')[:10]}...")
            print(f"   Source: Secure storage (no 1Password prompts!)")
        else:
            print("❌ SICON credentials not found")
        
        # Test SIFIN credentials  
        print("\n🔍 Testing SIFIN credentials...")
        sifin_creds = cred_manager.get_credentials('SIFIN')
        
        if sifin_creds:
            print(f"✅ SIFIN credentials found!")
            print(f"   Username: {sifin_creds.get('username', 'N/A')[:10]}...")
        else:
            print("❌ SIFIN credentials not found")
        
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
    import os
    
    # Set master password for testing
    os.environ['EDITORIAL_MASTER_PASSWORD'] = 'test_master_password'
    
    success = test_secure_integration()
    
    if success:
        print("\n🎉 SECURE CREDENTIAL INTEGRATION WORKING!")
        print("\n📋 Benefits:")
        print("✅ No 1Password authentication prompts")
        print("✅ Encrypted local storage")
        print("✅ Automated extraction ready")
        print("\n📋 Next steps:")
        print("1. Test extraction: python3 test_extraction_quick.py")
        print("2. Run full SICON: python3 run_unified_with_1password.py --journal SICON")
    else:
        print("\n❌ Integration needs more work")