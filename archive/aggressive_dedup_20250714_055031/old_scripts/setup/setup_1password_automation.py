#!/usr/bin/env python3
"""
Setup 1Password Integration for Editorial Scripts
One-time setup to enable fully automated extractions
"""

import subprocess
import sys
import os
from pathlib import Path

def check_1password_cli():
    """Check if 1Password CLI is installed"""
    print("🔍 Checking 1Password CLI installation...")
    
    try:
        result = subprocess.run(['op', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ 1Password CLI installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ 1Password CLI not working properly")
            return False
    except FileNotFoundError:
        print("❌ 1Password CLI not found")
        print("\n📦 INSTALLATION INSTRUCTIONS:")
        print("macOS: brew install --cask 1password-cli")
        print("Manual: https://1password.com/downloads/command-line/")
        return False
    except subprocess.TimeoutExpired:
        print("❌ 1Password CLI not responding")
        return False

def setup_1password_session():
    """Set up 1Password session"""
    print("\n🔐 Setting up 1Password session...")
    
    try:
        # Check if already signed in
        whoami = subprocess.run(['op', 'whoami'], 
                              capture_output=True, text=True, timeout=10)
        if whoami.returncode == 0:
            print(f"✅ Already signed in to 1Password as: {whoami.stdout.strip()}")
            return True
        
        # Need to sign in
        print("🔑 Signing in to 1Password...")
        print("💡 You may be prompted for your master password or biometrics")
        
        # Interactive signin
        signin = subprocess.run(['op', 'signin'], timeout=120)
        
        if signin.returncode == 0:
            print("✅ Successfully signed in to 1Password")
            return True
        else:
            print("❌ Failed to sign in to 1Password")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Sign-in timed out")
        return False
    except Exception as e:
        print(f"❌ Error setting up session: {e}")
        return False

def check_orcid_item():
    """Check if ORCID item exists in 1Password"""
    print("\n🔍 Checking for ORCID item in 1Password...")
    
    try:
        # List items to see if ORCID exists
        list_cmd = subprocess.run(['op', 'item', 'list', '--categories', 'Login'], 
                                capture_output=True, text=True, timeout=15)
        
        if list_cmd.returncode == 0:
            if 'ORCID' in list_cmd.stdout:
                print("✅ ORCID item found in 1Password")
                
                # Test credential retrieval
                try:
                    email_cmd = subprocess.run(['op', 'item', 'get', 'ORCID', '--fields', 'email'], 
                                             capture_output=True, text=True, timeout=10)
                    password_cmd = subprocess.run(['op', 'item', 'get', 'ORCID', '--fields', 'password'], 
                                                capture_output=True, text=True, timeout=10)
                    
                    if email_cmd.returncode == 0 and password_cmd.returncode == 0:
                        email = email_cmd.stdout.strip()
                        if email and '@' in email:
                            print(f"✅ ORCID credentials accessible: {email[:3]}****@****")
                            return True
                        else:
                            print("❌ ORCID email field is empty or invalid")
                            show_orcid_setup_instructions()
                            return False
                    else:
                        print("❌ Cannot access ORCID credentials")
                        show_orcid_setup_instructions()
                        return False
                        
                except Exception as e:
                    print(f"❌ Error testing ORCID credentials: {e}")
                    return False
            else:
                print("❌ ORCID item not found in 1Password")
                show_orcid_setup_instructions()
                return False
        else:
            print("❌ Cannot list 1Password items")
            return False
            
    except Exception as e:
        print(f"❌ Error checking ORCID item: {e}")
        return False

def show_orcid_setup_instructions():
    """Show detailed instructions for setting up ORCID item"""
    print("\n📋 ORCID ITEM SETUP INSTRUCTIONS:")
    print("=" * 50)
    print("1. Open the 1Password app on your computer")
    print("2. Click the '+' button to create a new item")
    print("3. Select 'Login' as the item type")
    print("4. Fill in the following:")
    print("   - Title: ORCID")
    print("   - Website: https://orcid.org")
    print("   - Username: (leave empty)")
    print("5. Add custom fields:")
    print("   - Field name: email")
    print("   - Field value: your ORCID email address")
    print("   - Field name: password") 
    print("   - Field value: your ORCID password")
    print("6. Save the item")
    print("7. Run this setup script again")
    print("\n💡 Make sure the field names are exactly 'email' and 'password'")

def test_credential_manager():
    """Test the Python credential manager integration"""
    print("\n🧪 Testing Python credential manager integration...")
    
    try:
        # Add paths
        sys.path.insert(0, str(Path(__file__).parent))
        sys.path.insert(0, str(Path(__file__).parent / 'core'))
        
        from core.credential_manager import get_credential_manager
        
        cred_manager = get_credential_manager()
        orcid_creds = cred_manager.get_journal_credentials('ORCID')
        
        if orcid_creds.get('email') and orcid_creds.get('password'):
            print(f"✅ Credential manager working: {orcid_creds['email'][:3]}****@****")
            return True
        else:
            print("❌ Credential manager cannot retrieve ORCID credentials")
            return False
            
    except Exception as e:
        print(f"❌ Error testing credential manager: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_setup():
    """Run complete 1Password setup"""
    print("🚀 1PASSWORD AUTOMATION SETUP")
    print("=" * 80)
    print("Setting up fully automated credential management for editorial scripts")
    print("=" * 80)
    
    success_steps = 0
    total_steps = 4
    
    # Step 1: Check CLI installation
    if check_1password_cli():
        success_steps += 1
    else:
        print("\n❌ Setup failed at step 1 - install 1Password CLI first")
        return False
    
    # Step 2: Set up session
    if setup_1password_session():
        success_steps += 1
    else:
        print("\n❌ Setup failed at step 2 - could not sign in to 1Password")
        return False
    
    # Step 3: Check ORCID item
    if check_orcid_item():
        success_steps += 1
    else:
        print("\n❌ Setup failed at step 3 - ORCID item not properly configured")
        return False
    
    # Step 4: Test credential manager
    if test_credential_manager():
        success_steps += 1
    else:
        print("\n❌ Setup failed at step 4 - credential manager integration broken")
        return False
    
    # Summary
    print(f"\n{'=' * 80}")
    print("🎯 SETUP SUMMARY")
    print("=" * 80)
    print(f"Completed steps: {success_steps}/{total_steps}")
    
    if success_steps == total_steps:
        print("\n🎉 SETUP COMPLETE - FULLY AUTOMATED!")
        print("✅ 1Password integration is working perfectly")
        print("\n🚀 Next steps:")
        print("1. Run: python3 run_unified_with_1password.py")
        print("2. Enjoy fully automated extractions!")
        print("\n💡 The system will now automatically:")
        print("   - Get credentials from 1Password")
        print("   - Authenticate with ORCID")
        print("   - Extract from SICON and SIFIN")
        print("   - Download all PDFs and reports")
        print("   - No manual intervention required!")
        return True
    else:
        print("\n❌ SETUP INCOMPLETE")
        print("Please follow the instructions above and run this script again")
        return False

if __name__ == "__main__":
    try:
        success = run_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)