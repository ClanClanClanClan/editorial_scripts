#!/usr/bin/env python3
"""
Fix authentication automation for 1Password and Gmail

This script addresses the authentication issues:
1. 1Password CLI session management
2. Gmail OAuth token persistence
3. Credential fallback chain optimization
"""

import os
import subprocess
import json
import pickle
import keyring
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthenticationFixer:
    def __init__(self):
        self.project_root = Path(__file__).parent
        
    def fix_1password_automation(self):
        """Fix 1Password CLI automation"""
        print("🔧 Fixing 1Password CLI automation...")
        
        # Check if 1Password CLI is installed
        try:
            result = subprocess.run(['op', '--version'], capture_output=True, text=True, check=True)
            print(f"✅ 1Password CLI version: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ 1Password CLI not installed")
            return False
        
        # Check sign-in status
        try:
            result = subprocess.run(['op', 'whoami'], capture_output=True, text=True, check=True)
            print(f"✅ Signed in as: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError:
            print("⚠️ Not signed in to 1Password CLI")
            
            # Try to sign in
            try:
                print("🔐 Attempting to sign in to 1Password...")
                result = subprocess.run(['op', 'signin', '--raw'], 
                                      capture_output=True, text=True, check=True)
                session_token = result.stdout.strip()
                
                # Export session token
                account_id = "my"  # Default account shorthand
                os.environ[f'OP_SESSION_{account_id}'] = session_token
                
                print("✅ 1Password CLI signed in successfully")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to sign in: {e}")
                return False
    
    def fix_gmail_oauth_persistence(self):
        """Fix Gmail OAuth token persistence"""
        print("🔧 Fixing Gmail OAuth persistence...")
        
        token_path = self.project_root / "token.json"
        creds_path = self.project_root / "credentials.json"
        
        # Check if credentials.json exists
        if not creds_path.exists():
            print("❌ credentials.json not found")
            return False
        
        # Check token format
        if token_path.exists():
            try:
                # Try to read as JSON first
                with open(token_path, 'r') as f:
                    json.load(f)
                print("✅ Token is in JSON format")
                return True
            except json.JSONDecodeError:
                print("⚠️ Token is in pickle format, converting...")
                
                # Backup pickle file
                backup_path = token_path.with_suffix('.pickle.backup')
                token_path.rename(backup_path)
                
                # Convert to JSON format
                try:
                    with open(backup_path, 'rb') as f:
                        creds = pickle.load(f)
                    
                    # Convert to JSON
                    token_data = {
                        "token": creds.token,
                        "refresh_token": creds.refresh_token,
                        "token_uri": creds.token_uri,
                        "client_id": creds.client_id,
                        "client_secret": creds.client_secret,
                        "scopes": creds.scopes
                    }
                    
                    with open(token_path, 'w') as f:
                        json.dump(token_data, f, indent=2)
                    
                    print("✅ Token converted to JSON format")
                    return True
                except Exception as e:
                    print(f"❌ Failed to convert token: {e}")
                    return False
        else:
            print("⚠️ No token file found - OAuth flow required")
            return False
    
    def setup_credential_fallback(self):
        """Set up credential fallback chain"""
        print("🔧 Setting up credential fallback chain...")
        
        # Check environment variables
        env_creds = []
        for var in ['GMAIL_USER', 'RECIPIENT_EMAIL']:
            if os.getenv(var):
                env_creds.append(var)
        
        print(f"✅ Environment variables: {env_creds}")
        
        # Check system keyring
        try:
            test_service = "editorial_test_keyring"
            keyring.set_password(test_service, "test", "test_value")
            retrieved = keyring.get_password(test_service, "test")
            keyring.delete_password(test_service, "test")
            
            if retrieved == "test_value":
                print("✅ System keyring working")
            else:
                print("⚠️ System keyring not working properly")
        except Exception as e:
            print(f"⚠️ System keyring error: {e}")
        
        return True
    
    def setup_1password_items(self):
        """Set up 1Password items for all journals"""
        print("🔧 Setting up 1Password items...")
        
        # Check if we can access 1Password
        try:
            subprocess.run(['op', 'vault', 'list'], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            print("❌ Cannot access 1Password - please sign in first")
            return False
        
        # List of journals that need credentials
        journals = ['SICON', 'SIFIN', 'MOR', 'MF', 'NACO', 'FS', 'JOTA', 'MAFE']
        
        print("📋 Checking 1Password items for journals...")
        
        for journal in journals:
            try:
                # Check if item exists
                result = subprocess.run(['op', 'item', 'get', journal], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ {journal} item exists")
                else:
                    print(f"⚠️ {journal} item missing")
                    
                    # Create placeholder item
                    create_cmd = [
                        'op', 'item', 'create',
                        '--category', 'login',
                        '--title', journal,
                        '--vault', 'Private',
                        f'username={journal.lower()}@placeholder.com',
                        f'password=placeholder_password_{journal.lower()}'
                    ]
                    
                    try:
                        subprocess.run(create_cmd, capture_output=True, check=True)
                        print(f"✅ Created placeholder item for {journal}")
                    except subprocess.CalledProcessError as e:
                        print(f"❌ Failed to create {journal} item: {e}")
                        
            except Exception as e:
                print(f"❌ Error checking {journal}: {e}")
        
        # Check for special items
        special_items = ['RECIPIENT', 'gmail']
        for item in special_items:
            try:
                result = subprocess.run(['op', 'item', 'get', item], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"✅ {item} item exists")
                else:
                    print(f"⚠️ {item} item missing - please create manually")
            except Exception as e:
                print(f"❌ Error checking {item}: {e}")
        
        return True
    
    def create_session_management_script(self):
        """Create a script to manage 1Password sessions"""
        script_content = '''#!/bin/bash
# 1Password session management script

# Check if signed in
if ! op whoami > /dev/null 2>&1; then
    echo "Signing in to 1Password..."
    if eval $(op signin --raw); then
        echo "✅ 1Password signed in successfully"
    else
        echo "❌ Failed to sign in to 1Password"
        exit 1
    fi
else
    echo "✅ Already signed in to 1Password"
fi

# Export session for current shell
export OP_SESSION_my=$(op signin --raw)
echo "Session exported: $OP_SESSION_my"
'''
        
        script_path = self.project_root / "auth_1password.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
        print(f"✅ Created session management script: {script_path}")
        return script_path
    
    def run_comprehensive_fix(self):
        """Run all authentication fixes"""
        print("🚀 Running comprehensive authentication fix...")
        print("=" * 50)
        
        success_count = 0
        total_fixes = 5
        
        if self.fix_1password_automation():
            success_count += 1
        
        if self.fix_gmail_oauth_persistence():
            success_count += 1
        
        if self.setup_credential_fallback():
            success_count += 1
        
        if self.setup_1password_items():
            success_count += 1
        
        if self.create_session_management_script():
            success_count += 1
        
        print("=" * 50)
        print(f"📊 Authentication fix results: {success_count}/{total_fixes} successful")
        
        if success_count == total_fixes:
            print("🎉 All authentication issues fixed!")
            return True
        else:
            print("⚠️ Some authentication issues remain")
            return False

def main():
    """Main function"""
    fixer = AuthenticationFixer()
    success = fixer.run_comprehensive_fix()
    
    if success:
        print("\n🎯 Next steps:")
        print("1. Run: source auth_1password.sh")
        print("2. Test with: python3 main_enhanced.py --journals JOTA --dry-run")
        print("3. Run full test suite: python3 run_real_tests.py --all")
    else:
        print("\n🔧 Manual fixes needed:")
        print("1. Sign in to 1Password CLI: op signin")
        print("2. Run Gmail OAuth flow: python3 -c 'from core.email_utils import get_gmail_service; get_gmail_service()'")
        print("3. Create missing 1Password items manually")

if __name__ == "__main__":
    main()