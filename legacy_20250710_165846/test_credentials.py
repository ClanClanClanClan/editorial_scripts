#!/usr/bin/env python3
"""
Test credential manager functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.credential_manager import get_credential_manager

def test_credential_manager():
    """Test credential manager functionality"""
    print("Testing credential manager...")
    
    try:
        cred_manager = get_credential_manager()
        print(f"✅ Credential manager created: {type(cred_manager).__name__}")
        
        # Test different journals
        journals = ["JOTA", "MAFE", "SICON", "SIFIN", "MF", "MOR", "NACO", "FS"]
        
        for journal in journals:
            print(f"\n--- Testing {journal} ---")
            try:
                creds = cred_manager.get_journal_credentials(journal)
                print(f"✅ {journal} credentials retrieved")
                print(f"   Username: {'Yes' if creds.get('username') else 'No'}")
                print(f"   Password: {'Yes' if creds.get('password') else 'No'}")
                print(f"   Email: {'Yes' if creds.get('email') else 'No'}")
            except Exception as e:
                print(f"❌ {journal} credentials failed: {e}")
        
        # Test ORCID credentials
        print(f"\n--- Testing ORCID ---")
        try:
            orcid_creds = cred_manager.get_orcid_credentials()
            print(f"✅ ORCID credentials retrieved")
            print(f"   Email: {'Yes' if orcid_creds.get('email') else 'No'}")
            print(f"   Password: {'Yes' if orcid_creds.get('password') else 'No'}")
        except Exception as e:
            print(f"❌ ORCID credentials failed: {e}")
    
    except Exception as e:
        print(f"❌ Credential manager setup failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_credential_manager()
    if success:
        print("\n✅ Credential manager tests completed")
    else:
        print("\n❌ Credential manager tests failed")
        sys.exit(1)