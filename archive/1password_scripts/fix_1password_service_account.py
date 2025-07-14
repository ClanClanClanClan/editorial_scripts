#!/usr/bin/env python3
"""
Fix 1Password Service Account setup - properly configure vault access
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(cmd, capture=True):
    """Run a command and return output"""
    try:
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout.strip(), result.stderr.strip(), result.returncode
        else:
            return subprocess.run(cmd, shell=True).returncode
    except Exception as e:
        return "", str(e), 1

def setup_service_account():
    """Setup 1Password service account with proper vault configuration"""
    
    print("🔧 FIXING 1PASSWORD SERVICE ACCOUNT SETUP")
    print("=" * 60)
    
    # Check if token is already set
    token = os.environ.get('OP_SERVICE_ACCOUNT_TOKEN')
    if not token:
        print("\n❌ No service account token found in environment")
        print("\n📋 To fix this:")
        print("1. Your token was already created and starts with: ops_eyJzaWduSW...")
        print("2. Add it to your shell profile manually:")
        print("\n   For zsh (default on Mac):")
        print(f"   echo 'export OP_SERVICE_ACCOUNT_TOKEN=\"ops_eyJzaWduSW...\"' >> ~/.zshrc")
        print(f"   source ~/.zshrc")
        print("\n3. Then run this script again")
        return False
    
    print("✅ Service account token found")
    
    # Get account info
    print("\n🔍 Getting account information...")
    stdout, stderr, code = run_command("op account get")
    if code == 0:
        print(f"✅ Account connected: {stdout}")
    else:
        print(f"❌ Failed to get account info: {stderr}")
        return False
    
    # List available vaults
    print("\n📂 Finding available vaults...")
    stdout, stderr, code = run_command("op vault list --format=json")
    
    if code != 0:
        print(f"❌ Failed to list vaults: {stderr}")
        return False
    
    try:
        vaults = json.loads(stdout)
        print(f"\n📋 Available vaults:")
        vault_names = []
        for vault in vaults:
            print(f"  - {vault['name']} (ID: {vault['id']})")
            vault_names.append(vault['name'])
        
        # Find the most likely vault
        orcid_vault = None
        for vault in vaults:
            vault_name = vault['name'].lower()
            if any(term in vault_name for term in ['personal', 'private', 'my', 'orcid', 'credential']):
                orcid_vault = vault['name']
                break
        
        if not orcid_vault and vaults:
            orcid_vault = vaults[0]['name']  # Use first vault as fallback
        
        if orcid_vault:
            print(f"\n✅ Selected vault: {orcid_vault}")
        
    except json.JSONDecodeError:
        print("⚠️  Could not parse vault list, will try common vault names")
        orcid_vault = "Personal"
    
    # Test ORCID credential access with vault specified
    print(f"\n🧪 Testing ORCID credential access in vault '{orcid_vault}'...")
    
    # Try to find ORCID item
    stdout, stderr, code = run_command(f'op item list --vault "{orcid_vault}" --format=json')
    if code != 0:
        print(f"❌ Failed to list items in vault: {stderr}")
        # Try without quotes
        stdout, stderr, code = run_command(f'op item list --vault {orcid_vault} --format=json')
    
    if code == 0:
        try:
            items = json.loads(stdout)
            orcid_items = [item for item in items if 'orcid' in item.get('title', '').lower()]
            
            if orcid_items:
                print(f"✅ Found {len(orcid_items)} ORCID-related items")
                for item in orcid_items[:3]:  # Show first 3
                    print(f"   - {item.get('title', 'Unknown')}")
            else:
                print("⚠️  No items with 'ORCID' in the name found")
                print("\n📋 All items in vault:")
                for item in items[:10]:  # Show first 10
                    print(f"   - {item.get('title', 'Unknown')}")
                if len(items) > 10:
                    print(f"   ... and {len(items) - 10} more")
        except:
            pass
    
    # Create helper scripts
    print("\n📝 Creating helper scripts...")
    
    # Create credential retrieval script
    get_creds_script = f'''#!/usr/bin/env python3
"""Get ORCID credentials from 1Password using service account"""

import subprocess
import json
import os

def get_orcid_credentials():
    """Get ORCID credentials from 1Password"""
    
    vault = "{orcid_vault}"
    
    # Try to find ORCID item
    cmd = f'op item list --vault "{{vault}}" --format=json'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error listing items: {{result.stderr}}")
        return None
    
    try:
        items = json.loads(result.stdout)
        
        # Find ORCID item
        orcid_item = None
        for item in items:
            if 'orcid' in item.get('title', '').lower():
                orcid_item = item
                break
        
        if not orcid_item:
            print("No ORCID item found in vault")
            print("Available items:")
            for item in items[:10]:
                print(f"  - {{item.get('title', 'Unknown')}}")
            return None
        
        # Get the full item details
        item_id = orcid_item['id']
        cmd = f'op item get {{item_id}} --vault "{{vault}}" --format=json'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error getting item details: {{result.stderr}}")
            return None
        
        item_details = json.loads(result.stdout)
        
        # Extract username and password
        username = None
        password = None
        
        for field in item_details.get('fields', []):
            if field.get('purpose') == 'USERNAME':
                username = field.get('value')
            elif field.get('purpose') == 'PASSWORD':
                password = field.get('value')
        
        if username and password:
            return {{'username': username, 'password': password}}
        else:
            print("Could not find username/password fields")
            return None
            
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {{e}}")
        return None

if __name__ == "__main__":
    creds = get_orcid_credentials()
    if creds:
        print(f"✅ Found ORCID credentials")
        print(f"   Username: {{creds['username']}}")
        print(f"   Password: {'*' * len(creds['password'])}}")
    else:
        print("❌ Failed to retrieve ORCID credentials")
'''
    
    script_path = Path("get_orcid_credentials.py")
    with open(script_path, 'w') as f:
        f.write(get_creds_script)
    script_path.chmod(0o755)
    print(f"✅ Created {script_path}")
    
    # Create test script
    test_script = f'''#!/bin/bash
# Test 1Password service account access

echo "🧪 Testing 1Password Service Account..."
echo

echo "1. Account info:"
op account get
echo

echo "2. Available vaults:"
op vault list
echo

echo "3. Items in {orcid_vault} vault:"
op item list --vault "{orcid_vault}" --format=json | jq -r '.[] | .title' 2>/dev/null || op item list --vault "{orcid_vault}"
echo

echo "4. Testing credential retrieval:"
python3 get_orcid_credentials.py
'''
    
    test_path = Path("test_1password_service.sh")
    with open(test_path, 'w') as f:
        f.write(test_script)
    test_path.chmod(0o755)
    print(f"✅ Created {test_path}")
    
    # Update credential manager to use vault
    print("\n🔧 Updating credential manager...")
    cred_manager_path = Path("core/credential_manager.py")
    
    if cred_manager_path.exists():
        with open(cred_manager_path, 'r') as f:
            content = f.read()
        
        # Add vault parameter to op commands
        if '--vault' not in content:
            print("📝 Patching credential_manager.py to include vault...")
            # This would need the actual patching logic
            print("⚠️  Manual update needed - add --vault parameter to op commands")
    
    print("\n✅ Setup complete!")
    print("\n📋 Next steps:")
    print(f"1. Test with: ./test_1password_service.sh")
    print(f"2. Run extraction with: python3 run_unified_with_1password.py --journal SICON")
    print(f"\nℹ️  Default vault set to: {orcid_vault}")
    print("   If ORCID credentials are in a different vault, update the scripts accordingly")
    
    return True


if __name__ == "__main__":
    setup_service_account()