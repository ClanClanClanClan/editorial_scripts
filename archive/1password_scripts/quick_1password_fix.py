#!/usr/bin/env python3
"""
Quick 1Password fix - directly patch the credential manager to use vault
"""

import os
import subprocess
from pathlib import Path

def quick_1password_fix():
    """Quick fix for 1Password service account issue"""
    
    print("🔧 QUICK 1PASSWORD FIX")
    print("=" * 30)
    
    # Check if we have a working 1Password setup at all
    print("\n1️⃣ Testing basic 1Password CLI...")
    
    # First check if 1Password CLI is working
    result = subprocess.run(['op', '--version'], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ 1Password CLI not installed or not working")
        return False
    
    print(f"✅ 1Password CLI version: {result.stdout.strip()}")
    
    # Check if we can access without service account (interactive login)
    print("\n2️⃣ Testing interactive login...")
    result = subprocess.run(['op', 'account', 'list'], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Interactive login available")
        
        # Get vaults
        result = subprocess.run(['op', 'vault', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Can list vaults")
            vaults = result.stdout.strip().split('\n')[1:]  # Skip header
            if vaults:
                vault_name = vaults[0].split()[0]  # First vault name
                print(f"✅ Using vault: {vault_name}")
                
                # Create a working credential manager patch
                patch_credential_manager(vault_name)
                
                return True
        
    print("⚠️ Interactive login not available, trying alternative approach...")
    
    # Alternative: Just use environment variables
    print("\n3️⃣ Using environment variables fallback...")
    
    # Check if ORCID credentials are in environment
    orcid_email = os.getenv('ORCID_EMAIL')
    orcid_password = os.getenv('ORCID_PASSWORD')
    
    if orcid_email and orcid_password:
        print("✅ ORCID credentials found in environment")
        create_env_based_solution()
        return True
    
    print("❌ No working credentials found")
    print("\n📋 Manual fix required:")
    print("1. Set environment variables:")
    print("   export ORCID_EMAIL='your.email@example.com'")
    print("   export ORCID_PASSWORD='your_password'")
    print("2. Or use interactive 1Password login:")
    print("   op signin")
    
    return False


def patch_credential_manager(vault_name="Personal"):
    """Patch the credential manager to use 1Password with vault"""
    
    cred_manager_path = Path("src/core/credential_manager.py")
    
    if not cred_manager_path.exists():
        print("❌ Credential manager not found")
        return
    
    # Read current content
    with open(cred_manager_path, 'r') as f:
        content = f.read()
    
    # Add 1Password integration
    onepassword_integration = f'''
    def _get_1password_credentials(self, item_name: str) -> Optional[Dict[str, str]]:
        """Get credentials from 1Password"""
        try:
            import subprocess
            import json
            
            # Try to get item with vault specified
            cmd = ['op', 'item', 'get', item_name, '--vault', '{vault_name}', '--format=json']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                # Try without vault
                cmd = ['op', 'item', 'get', item_name, '--format=json']
                result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning(f"Could not get 1Password item: {{item_name}}")
                return None
            
            item = json.loads(result.stdout)
            
            # Extract username and password
            username = None
            password = None
            
            for field in item.get('fields', []):
                if field.get('purpose') == 'USERNAME':
                    username = field.get('value')
                elif field.get('purpose') == 'PASSWORD':
                    password = field.get('value')
            
            if username and password:
                return {{
                    'username': username,
                    'password': password,
                    'email': username
                }}
            
        except Exception as e:
            logger.warning(f"1Password error: {{e}}")
        
        return None
'''
    
    # Update SIAM credentials method to use 1Password
    updated_siam_method = '''
    def _get_siam_credentials(self) -> Optional[Dict[str, str]]:
        """Get SIAM (ORCID) credentials for SICON/SIFIN"""
        
        # Try 1Password first
        op_creds = self._get_1password_credentials('ORCID')
        if op_creds:
            return op_creds
        
        # Fallback to settings and environment
        username = None
        password = None
        
        # Try settings first
        if self.settings:
            username = self.settings.orcid_email
            password = self.settings.orcid_password
        
        # Try environment variables as fallback
        if not username:
            username = os.getenv('ORCID_EMAIL')
        if not password:
            password = os.getenv('ORCID_PASSWORD')
        
        if username and password:
            return {
                'username': username,
                'password': password,
                'email': username  # ORCID uses email as username
            }
        
        return None
'''
    
    # Find and replace the SIAM credentials method
    import re
    pattern = r'def _get_siam_credentials\(self\).*?return None'
    replacement = updated_siam_method.strip()
    
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Add the 1Password helper method before the existing methods
    if '_get_1password_credentials' not in content:
        # Find where to insert (before first private method)
        insertion_point = content.find('def _get_siam_credentials')
        if insertion_point > 0:
            content = content[:insertion_point] + onepassword_integration + '\n    ' + content[insertion_point:]
    
    # Write back
    with open(cred_manager_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Patched credential manager to use vault: {vault_name}")


def create_env_based_solution():
    """Create a simple environment-based credential solution"""
    
    env_template = '''
# Add these to your ~/.zshrc or ~/.bashrc:

export ORCID_EMAIL="your.orcid.email@example.com"
export ORCID_PASSWORD="your_orcid_password"

# For other journals (when implemented):
export SCHOLARONE_EMAIL="your.scholarone.email@example.com"  
export SCHOLARONE_PASSWORD="your_scholarone_password"

# Then run:
source ~/.zshrc
'''
    
    with open("CREDENTIALS_SETUP.txt", "w") as f:
        f.write(env_template)
    
    print("✅ Created CREDENTIALS_SETUP.txt with environment variable template")


if __name__ == "__main__":
    success = quick_1password_fix()
    
    if success:
        print("\n✅ 1Password fix complete!")
        print("\n📋 Test with:")
        print("   python3 tests/test_sicon_fixed.py")
    else:
        print("\n❌ Fix incomplete - manual setup required")
        print("   See CREDENTIALS_SETUP.txt for environment variable approach")