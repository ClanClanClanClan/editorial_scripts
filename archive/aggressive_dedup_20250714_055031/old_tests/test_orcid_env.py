#!/usr/bin/env python3
"""
Test ORCID credentials from environment variables
Simple test to verify credential availability
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_env_credentials():
    """Test environment variable credentials"""
    print("🔍 TESTING ORCID CREDENTIALS")
    print("=" * 60)
    
    # Check environment variables
    print("\n📋 Checking environment variables...")
    orcid_email = os.getenv('ORCID_EMAIL')
    orcid_password = os.getenv('ORCID_PASSWORD')
    
    if orcid_email:
        print(f"✅ ORCID_EMAIL found: {orcid_email[:3]}****")
    else:
        print("❌ ORCID_EMAIL not set")
    
    if orcid_password:
        print(f"✅ ORCID_PASSWORD found: {'*' * 8}")
    else:
        print("❌ ORCID_PASSWORD not set")
    
    # Check settings file
    print("\n📋 Checking settings configuration...")
    try:
        from src.infrastructure.config import settings
        
        if hasattr(settings, 'orcid_email') and settings.orcid_email:
            print(f"✅ settings.orcid_email: {settings.orcid_email[:3]}****")
        else:
            print("❌ settings.orcid_email not configured")
        
        if hasattr(settings, 'orcid_password') and settings.orcid_password:
            print(f"✅ settings.orcid_password: {'*' * 8}")
        else:
            print("❌ settings.orcid_password not configured")
            
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    if (orcid_email and orcid_password) or \
       (hasattr(settings, 'orcid_email') and settings.orcid_email and \
        hasattr(settings, 'orcid_password') and settings.orcid_password):
        print("✅ ORCID credentials are available!")
        print("\n🚀 You can run the SIAM scraper with:")
        print("   python test_siam_scraper.py")
        print("   or")
        print("   python demo_stealth_scraper.py")
        return True
    else:
        print("❌ ORCID credentials not found")
        print("\n📋 To set credentials, use one of these methods:")
        print("\n1. Environment variables:")
        print("   export ORCID_EMAIL='your@email.com'")
        print("   export ORCID_PASSWORD='your_password'")
        print("\n2. Create a .env file with:")
        print("   ORCID_EMAIL=your@email.com")
        print("   ORCID_PASSWORD=your_password")
        print("\n3. Use 1Password CLI:")
        print("   - Install: https://1password.com/downloads/command-line/")
        print("   - Sign in: eval $(op signin)")
        print("   - Create ORCID item in 1Password")
        return False

if __name__ == "__main__":
    success = test_env_credentials()
    sys.exit(0 if success else 1)