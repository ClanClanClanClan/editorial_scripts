#!/usr/bin/env python3
"""
Debug credential access
"""

from core.credential_manager import get_credential_manager
import os

def debug_credentials():
    """Check what credentials are available"""
    
    print("Credential Debug")
    print("=" * 60)
    
    # Get credential manager
    cred_manager = get_credential_manager()
    
    print("\n1. Testing ORCID credentials from 1Password/env:")
    
    # Try to get ORCID credentials
    orcid_email = cred_manager.get('ORCID', 'email')
    orcid_password = cred_manager.get('ORCID', 'password')
    
    print(f"   ORCID email from manager: {'Found' if orcid_email else 'Not found'}")
    print(f"   ORCID password from manager: {'Found' if orcid_password else 'Not found'}")
    
    # Check environment
    env_user = os.getenv('ORCID_USER') or os.getenv('ORCID_USERNAME')
    env_pass = os.getenv('ORCID_PASS') or os.getenv('ORCID_PASSWORD')
    
    print(f"\n2. Environment variables:")
    print(f"   ORCID_USER/USERNAME: {'Set' if env_user else 'Not set'}")
    print(f"   ORCID_PASS/PASSWORD: {'Set' if env_pass else 'Not set'}")
    
    # Check other journal credentials
    print("\n3. Testing other journal credentials:")
    journals = ['SICON', 'SIFIN', 'MOR', 'MF']
    
    for journal in journals:
        creds = cred_manager.get_journal_credentials(journal)
        has_creds = any(creds.values())
        print(f"   {journal}: {'Found' if has_creds else 'Not found'}")
    
    print("\n4. Credential providers available:")
    for i, provider in enumerate(cred_manager.providers):
        print(f"   {i+1}. {provider.__class__.__name__}")
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    if orcid_email and orcid_password:
        print("✅ ORCID credentials are available!")
    elif env_user and env_pass:
        print("✅ ORCID credentials available from environment")
    else:
        print("❌ No ORCID credentials found")
        print("\nTo fix this, either:")
        print("1. Sign in to 1Password: op signin")
        print("2. Set environment variables:")
        print("   export ORCID_USER='your_orcid_email'")
        print("   export ORCID_PASS='your_orcid_password'")


if __name__ == "__main__":
    debug_credentials()