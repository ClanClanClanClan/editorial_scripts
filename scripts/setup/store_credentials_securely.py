#!/usr/bin/env python3
"""
Store your already-exported credentials securely
This script provides multiple options for secure credential storage
"""

import os
import sys
import keyring
from pathlib import Path

def store_credentials_securely():
    """Guide user through storing credentials securely"""
    
    print("🔐 Secure Credential Storage for Editorial Scripts")
    print("=" * 50)
    print("\nSince you've already exported your credentials, I'll help you store them securely.")
    print("\nPlease run ONE of the following commands to set your credentials:")
    print("\n1. Export credentials in current shell (temporary):")
    print('   export ORCID_EMAIL="your.actual@email.com"')
    print('   export ORCID_PASSWORD="your_actual_password"')
    
    print("\n2. Add to your shell profile (permanent):")
    print("   For zsh (macOS default):")
    print('   echo \'export ORCID_EMAIL="your.actual@email.com"\' >> ~/.zshrc')
    print('   echo \'export ORCID_PASSWORD="your_actual_password"\' >> ~/.zshrc')
    print('   source ~/.zshrc')
    
    print("\n3. Create a secure .env file:")
    env_path = Path.cwd() / ".env.production"
    print(f"   Create {env_path} with:")
    print('   ORCID_EMAIL="your.actual@email.com"')
    print('   ORCID_PASSWORD="your_actual_password"')
    
    print("\n4. Use the secure credential manager interactively:")
    print("   python3 secure_credential_manager.py")
    print("   (This will prompt for credentials and store them securely)")
    
    print("\n" + "=" * 50)
    print("\n🧪 After setting credentials, test the ultimate system:")
    print("   cd editorial_scripts_ultimate")
    print("   python3 main.py sicon --test")
    
    print("\n📊 Expected result with real credentials:")
    print("   ✅ 4+ manuscripts found")
    print("   ✅ 13+ referees extracted")
    print("   ✅ 4+ PDFs downloaded")
    print("   ✅ System restored to July 11 baseline!")

if __name__ == "__main__":
    store_credentials_securely()