#!/bin/bash
# Comprehensive authentication setup script

echo "🔐 Setting up authentication for Editorial Scripts..."

# 1. Set up 1Password CLI session
echo "1️⃣ Setting up 1Password CLI..."
if ! command -v op &> /dev/null; then
    echo "❌ 1Password CLI not installed. Install from: https://1password.com/downloads/command-line/"
    exit 1
fi

# Sign in to 1Password and keep session alive
if ! op whoami &> /dev/null; then
    echo "🔐 Signing in to 1Password..."
    eval $(op signin)
    if [ $? -eq 0 ]; then
        echo "✅ 1Password CLI signed in successfully"
    else
        echo "❌ Failed to sign in to 1Password"
        exit 1
    fi
else
    echo "✅ Already signed in to 1Password"
fi

# 2. Set up environment variables for session persistence
echo "2️⃣ Setting up environment variables..."
ACCOUNT_ID=$(op account list --format=json | jq -r '.[0].user_uuid' 2>/dev/null || echo "my")
export OP_SESSION_${ACCOUNT_ID}=$(op signin --raw 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "✅ 1Password session token exported"
    echo "export OP_SESSION_${ACCOUNT_ID}=${OP_SESSION_${ACCOUNT_ID}}" >> ~/.bashrc
    echo "export OP_SESSION_${ACCOUNT_ID}=${OP_SESSION_${ACCOUNT_ID}}" >> ~/.zshrc
else
    echo "⚠️ Could not export session token"
fi

# 3. Test 1Password access
echo "3️⃣ Testing 1Password access..."
if op vault list &> /dev/null; then
    echo "✅ 1Password vault access working"
else
    echo "❌ Cannot access 1Password vaults"
    exit 1
fi

# 4. Check Gmail credentials
echo "4️⃣ Checking Gmail credentials..."
if [ -f "credentials.json" ]; then
    echo "✅ Gmail credentials.json found"
else
    echo "❌ Gmail credentials.json not found"
    echo "   Download from Google Cloud Console and place in project root"
    exit 1
fi

if [ -f "token.json" ]; then
    echo "✅ Gmail token.json found"
else
    echo "⚠️ Gmail token.json not found - OAuth flow required"
    echo "   Run: python3 -c 'from core.email_utils import get_gmail_service; get_gmail_service()'"
fi

# 5. Set up Chrome profile directory
echo "5️⃣ Setting up Chrome profile directory..."
CHROME_PROFILE_DIR="$HOME/chrome_profiles"
mkdir -p "$CHROME_PROFILE_DIR"
chmod 755 "$CHROME_PROFILE_DIR"
echo "✅ Chrome profile directory: $CHROME_PROFILE_DIR"

# 6. Create authentication verification script
echo "6️⃣ Creating verification script..."
cat > verify_auth.py << 'EOF'
#!/usr/bin/env python3
"""Verify authentication setup"""

import subprocess
import os
import json
from core.credential_manager import get_credential_manager

def check_1password():
    try:
        result = subprocess.run(['op', 'whoami'], capture_output=True, text=True, check=True)
        print(f"✅ 1Password: {result.stdout.strip()}")
        return True
    except:
        print("❌ 1Password: Not signed in")
        return False

def check_gmail():
    try:
        from core.email_utils import get_gmail_service
        service = get_gmail_service()
        profile = service.users().getProfile(userId='me').execute()
        print(f"✅ Gmail: {profile['emailAddress']}")
        return True
    except Exception as e:
        print(f"❌ Gmail: {e}")
        return False

def check_credentials():
    try:
        cred_manager = get_credential_manager()
        creds = cred_manager.get_journal_credentials("JOTA")
        print(f"✅ Credentials: Manager working")
        return True
    except Exception as e:
        print(f"❌ Credentials: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Verifying authentication setup...")
    results = []
    results.append(check_1password())
    results.append(check_gmail())
    results.append(check_credentials())
    
    success = sum(results)
    total = len(results)
    
    print(f"\n📊 Authentication status: {success}/{total} working")
    
    if success == total:
        print("🎉 All authentication systems working!")
    else:
        print("⚠️ Some authentication issues remain")
EOF

chmod +x verify_auth.py

echo "✅ Authentication setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Source this script: source setup_auth.sh"
echo "2. Verify setup: python3 verify_auth.py"
echo "3. Test with: python3 main_enhanced.py --journals JOTA --dry-run"
echo ""
echo "💡 For persistent sessions, add to your shell profile:"
echo "   echo 'eval \$(op signin)' >> ~/.bashrc"