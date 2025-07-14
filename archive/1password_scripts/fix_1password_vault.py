#!/usr/bin/env python3
"""
Quick fix for 1Password vault issue
"""

import subprocess
import json
import os

def fix_1password_vault():
    """Fix 1Password service account vault access"""
    
    print("🔧 FIXING 1PASSWORD VAULT ACCESS")
    print("=" * 50)
    
    # Check if token exists
    token = os.environ.get('OP_SERVICE_ACCOUNT_TOKEN')
    if not token:
        print("\n❌ No service account token found")
        print("\n📋 Please set your token:")
        print("export OP_SERVICE_ACCOUNT_TOKEN='ops_eyJzaWduSW...'")
        return False
    
    print("✅ Service account token found")
    
    # List vaults
    print("\n📂 Available vaults:")
    result = subprocess.run(['op', 'vault', 'list', '--format=json'], 
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False
    
    try:
        vaults = json.loads(result.stdout)
        vault_names = []
        
        for vault in vaults:
            name = vault['name']
            vault_names.append(name)
            print(f"  - {name}")
        
        # Use first vault or "Personal" if available
        default_vault = "Personal" if "Personal" in vault_names else vault_names[0]
        print(f"\n✅ Using vault: {default_vault}")
        
        # Test listing items in vault
        print(f"\n🧪 Testing access to '{default_vault}' vault...")
        result = subprocess.run(['op', 'item', 'list', '--vault', default_vault], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Can access vault items")
            
            # Look for ORCID item
            result = subprocess.run(['op', 'item', 'list', '--vault', default_vault, '--format=json'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                items = json.loads(result.stdout)
                orcid_items = [item for item in items if 'orcid' in item.get('title', '').lower()]
                
                if orcid_items:
                    print(f"✅ Found {len(orcid_items)} ORCID item(s)")
                    for item in orcid_items:
                        print(f"   - {item['title']}")
                else:
                    print("⚠️  No ORCID items found. Available items:")
                    for item in items[:5]:
                        print(f"   - {item.get('title', 'Unknown')}")
        else:
            print(f"❌ Cannot access vault: {result.stderr}")
            return False
        
        # Update credential manager
        print("\n🔧 Creating updated credential manager...")
        
        updated_cred_manager = f'''
def get_journal_credentials(journal_name: str) -> dict:
    """Get credentials from 1Password using service account with vault"""
    
    vault = "{default_vault}"
    
    try:
        # List items in vault to find ORCID
        cmd = ['op', 'item', 'list', '--vault', vault, '--format=json']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error listing items: {{result.stderr}}")
            return {{}}")
        
        items = json.loads(result.stdout)
        
        # Find ORCID item
        orcid_item = None
        for item in items:
            if 'orcid' in item.get('title', '').lower():
                orcid_item = item
                break
        
        if not orcid_item:
            print("No ORCID item found")
            return {{}}")
        
        # Get item details
        cmd = ['op', 'item', 'get', orcid_item['id'], '--vault', vault, '--format=json']
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return {{}}")
        
        item_details = json.loads(result.stdout)
        
        # Extract credentials
        username = None
        password = None
        
        for field in item_details.get('fields', []):
            if field.get('purpose') == 'USERNAME':
                username = field.get('value')
            elif field.get('purpose') == 'PASSWORD':
                password = field.get('value')
        
        return {{"email": username, "password": password}}
        
    except Exception as e:
        print(f"Error getting credentials: {{e}}")
        return {{}}")
'''
        
        # Save to file
        with open("updated_credential_manager.py", "w") as f:
            f.write(updated_cred_manager)
        
        print("✅ Created updated_credential_manager.py")
        
        # Create test script
        test_script = f'''#!/bin/bash
echo "Testing 1Password access..."
echo

echo "1. Vault access:"
op item list --vault "{default_vault}"
echo

echo "2. ORCID credentials test:"
python3 -c "
import subprocess
import json

# Find ORCID item
result = subprocess.run(['op', 'item', 'list', '--vault', '{default_vault}', '--format=json'], capture_output=True, text=True)
items = json.loads(result.stdout)
orcid_items = [item for item in items if 'orcid' in item.get('title', '').lower()]

if orcid_items:
    print(f'Found ORCID item: {{orcid_items[0][\"title\"]}}')
    # Get details
    item_id = orcid_items[0]['id']
    result = subprocess.run(['op', 'item', 'get', item_id, '--vault', '{default_vault}', '--format=json'], capture_output=True, text=True)
    item_details = json.loads(result.stdout)
    
    for field in item_details.get('fields', []):
        if field.get('purpose') == 'USERNAME':
            print(f'Username: {{field.get(\"value\")}}')
        elif field.get('purpose') == 'PASSWORD':
            print(f'Password: {{\"*\" * len(field.get(\"value\", \"\"))}}')
else:
    print('No ORCID item found')
"
'''
        
        with open("test_1password_fixed.sh", "w") as f:
            f.write(test_script)
        
        os.chmod("test_1password_fixed.sh", 0o755)
        print("✅ Created test_1password_fixed.sh")
        
        print("\n📋 Next steps:")
        print("1. Test with: ./test_1password_fixed.sh")
        print("2. Update core/credential_manager.py with vault parameter")
        print(f"3. Use vault '{default_vault}' in all op commands")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON error: {e}")
        return False


if __name__ == "__main__":
    fix_1password_vault()