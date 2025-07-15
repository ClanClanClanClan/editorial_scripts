#!/usr/bin/env python3
"""
Quick setup script for storing credentials in system keychain
"""

import keyring
import os
from pathlib import Path

def setup_keychain_credentials():
    """Store credentials directly in system keychain"""
    
    print("🔐 Setting up credentials in system keychain...")
    
    # Check if credentials are already in environment
    orcid_email = os.getenv("ORCID_EMAIL")
    orcid_password = os.getenv("ORCID_PASSWORD")
    
    if orcid_email and orcid_password:
        print(f"✅ Found credentials in environment:")
        print(f"   ORCID_EMAIL: {orcid_email}")
        print(f"   ORCID_PASSWORD: {'*' * len(orcid_password)}")
        
        # Store in keychain
        keyring.set_password("editorial_scripts", "ORCID_EMAIL", orcid_email)
        keyring.set_password("editorial_scripts", "ORCID_PASSWORD", orcid_password)
        
        print("\n✅ Credentials stored in system keychain!")
        
        # Create loader script
        credential_dir = Path.home() / ".editorial_scripts"
        credential_dir.mkdir(exist_ok=True, mode=0o700)
        
        loader_script = f"""#!/bin/bash
# Load credentials from system keychain
export ORCID_EMAIL=$(python3 -c "import keyring; print(keyring.get_password('editorial_scripts', 'ORCID_EMAIL'))")
export ORCID_PASSWORD=$(python3 -c "import keyring; print(keyring.get_password('editorial_scripts', 'ORCID_PASSWORD'))")

echo "✅ Credentials loaded from keychain"
echo "   ORCID_EMAIL: $ORCID_EMAIL"
"""
        
        script_path = credential_dir / "load_credentials.sh"
        script_path.write_text(loader_script)
        script_path.chmod(0o700)
        
        print(f"\n📌 Created loader script: {script_path}")
        print("\n🎯 To use credentials in future sessions:")
        print(f"   source {script_path}")
        print("\n🧪 To test the ultimate system now:")
        print("   cd editorial_scripts_ultimate")
        print("   python3 main.py sicon --test")
        
    else:
        print("❌ No credentials found in environment!")
        print("\nPlease export your credentials first:")
        print('   export ORCID_EMAIL="your.email@example.com"')
        print('   export ORCID_PASSWORD="your_password"')
        print("\nThen run this script again.")

if __name__ == "__main__":
    setup_keychain_credentials()