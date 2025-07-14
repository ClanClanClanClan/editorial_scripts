#!/usr/bin/env python3
"""
Setup 1Password automatic authentication
"""

import subprocess
import os
import sys
from pathlib import Path

def setup_1password_session():
    """Setup 1Password session for automatic access"""
    print("🔑 Setting up 1Password session...")
    
    # Check if already signed in
    try:
        result = subprocess.run(['op', 'whoami'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 1Password session already active")
            return True
    except:
        pass
    
    # Check if we have accounts configured
    try:
        accounts_result = subprocess.run(['op', 'account', 'list'], 
                                       capture_output=True, text=True)
        if accounts_result.returncode != 0:
            print("❌ No 1Password accounts configured")
            return False
    except:
        print("❌ 1Password CLI not available")
        return False
    
    # Try to sign in automatically
    try:
        print("🔐 Attempting automatic signin...")
        signin_result = subprocess.run(['op', 'signin', '--account', 'my.1password.eu'], 
                                     input='\n', text=True, timeout=30)
        if signin_result.returncode == 0:
            print("✅ Successfully signed in to 1Password")
            return True
        else:
            print(f"❌ Signin failed: {signin_result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Signin timed out")
        return False
    except Exception as e:
        print(f"❌ Signin error: {e}")
        return False

def test_credential_access():
    """Test that we can access ORCID credentials"""
    print("\n🧪 Testing credential access...")
    
    try:
        # Test userId field
        userId_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=userId'], 
                                   capture_output=True, text=True, timeout=10)
        
        # Test password field  
        password_cmd = subprocess.run(['op', 'item', 'get', 'Orcid', '--fields=password'],
                                     capture_output=True, text=True, timeout=10)
        
        if userId_cmd.returncode == 0 and password_cmd.returncode == 0:
            userId = userId_cmd.stdout.strip()
            print(f"✅ Successfully retrieved ORCID credentials: {userId[:3]}****")
            return True
        else:
            print(f"❌ Failed to retrieve credentials")
            print(f"   userId error: {userId_cmd.stderr}")
            print(f"   password error: {password_cmd.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Credential test error: {e}")
        return False

def main():
    """Main setup process"""
    print("🛠️  1PASSWORD AUTOMATIC SETUP")
    print("=" * 50)
    
    # Step 1: Setup session
    if not setup_1password_session():
        print("\n❌ Failed to setup 1Password session")
        sys.exit(1)
    
    # Step 2: Test credential access
    if not test_credential_access():
        print("\n❌ Failed to access credentials")
        sys.exit(1)
    
    print("\n🎉 1Password setup complete!")
    print("✅ Session established")
    print("✅ Credentials accessible")
    print("✅ Ready for automatic scraping")

if __name__ == "__main__":
    main()