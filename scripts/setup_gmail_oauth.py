#!/usr/bin/env python3
"""
Gmail OAuth Setup Helper

Automates the Gmail API OAuth flow for ECC extractors.
Creates the necessary token files for 2FA and FS extraction.
"""

import os
import pickle
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("❌ Missing Google libraries. Installing...")
    os.system("pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

# Gmail API scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# File paths
CONFIG_DIR = project_root / "config"
CREDENTIALS_FILE = CONFIG_DIR / "gmail_credentials.json"
TOKEN_FILE = CONFIG_DIR / "gmail_token.json"
TOKEN_PICKLE = CONFIG_DIR / "gmail_token.pickle"


def check_credentials_file():
    """Check if credentials file exists."""
    if not CREDENTIALS_FILE.exists():
        print(f"❌ Credentials file not found: {CREDENTIALS_FILE}")
        print(f"\n📝 To create credentials:")
        print(f"   1. Go to https://console.cloud.google.com/")
        print(f"   2. Create/select a project")
        print(f"   3. Enable Gmail API")
        print(f"   4. Create OAuth 2.0 credentials (Desktop app)")
        print(f"   5. Download JSON and save as: {CREDENTIALS_FILE}")
        print(f"\n   See docs/GMAIL_OAUTH_SETUP.md for detailed instructions")
        return False

    print(f"✅ Found credentials file: {CREDENTIALS_FILE}")
    return True


def run_oauth_flow():
    """Run OAuth flow to get user authorization."""
    creds = None

    # Check for existing token
    if TOKEN_PICKLE.exists():
        print(f"📄 Loading existing token from {TOKEN_PICKLE}...")
        with open(TOKEN_PICKLE, "rb") as token:
            creds = pickle.load(token)

    # If no valid credentials, start OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            try:
                creds.refresh(Request())
                print("✅ Token refreshed successfully")
            except Exception as e:
                print(f"❌ Token refresh failed: {e}")
                print("   Starting new authorization flow...")
                creds = None

        if not creds:
            print(f"\n🔐 Starting OAuth authorization flow...")
            print(f"   Your browser will open for authorization")
            print(f"   Select your ETH email account")
            print(f"   Grant Gmail read/send permissions")

            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)

            creds = flow.run_local_server(port=0)
            print("✅ Authorization successful!")

        # Save credentials
        print(f"\n💾 Saving credentials...")

        # Save as JSON (for compatibility)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
        print(f"   ✅ Saved JSON token: {TOKEN_FILE}")

        # Save as pickle (for backward compatibility)
        with open(TOKEN_PICKLE, "wb") as token:
            pickle.dump(creds, token)
        print(f"   ✅ Saved pickle token: {TOKEN_PICKLE}")

    else:
        print("✅ Valid token already exists")

    return creds


def test_gmail_connection(creds):
    """Test Gmail API connection."""
    print(f"\n🧪 Testing Gmail API connection...")

    try:
        from googleapiclient.discovery import build

        service = build("gmail", "v1", credentials=creds)

        # Test by fetching profile
        profile = service.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress")

        print(f"✅ Successfully connected to Gmail")
        print(f"   Email: {email}")
        print(f"   Total messages: {profile.get('messagesTotal', 'Unknown')}")

        # Test search (for 2FA codes)
        results = (
            service.users()
            .messages()
            .list(userId="me", q="newer_than:1d subject:verification", maxResults=1)
            .execute()
        )

        msg_count = len(results.get("messages", []))
        print(f"   Recent verification emails: {msg_count}")

        return True

    except Exception as e:
        print(f"❌ Gmail API test failed: {e}")
        return False


def print_summary():
    """Print setup summary and next steps."""
    print(f"\n{'='*80}")
    print(f"📋 GMAIL OAUTH SETUP SUMMARY")
    print(f"{'='*80}")

    print(f"\n✅ Setup Complete!")
    print(f"\n📁 Files created:")
    print(f"   • {TOKEN_FILE}")
    print(f"   • {TOKEN_PICKLE}")

    print(f"\n🎯 You can now:")
    print(f"   1. Use FS extractor (Gmail-based)")
    print(f"   2. Automatic 2FA code retrieval for MF/MOR")

    print(f"\n🧪 Test FS extractor:")
    print(f'   python3 -c "')
    print(f"   import asyncio")
    print(f"   from src.ecc.adapters.journals.fs import FSAdapter")
    print(f"   ")
    print(f"   async def test():")
    print(f"       async with FSAdapter() as adapter:")
    print(f"           manuscripts = await adapter.fetch_all_manuscripts()")
    print(f"           print(f'Found {{len(manuscripts)}} manuscripts')")
    print(f"   ")
    print(f"   asyncio.run(test())")
    print(f'   "')

    print(f"\n💡 Token will auto-refresh when expired")
    print(f"   No need to re-run this script unless you change credentials")

    print(f"\n{'='*80}")


def main():
    """Main entry point."""
    print(f"{'='*80}")
    print(f"🔐 GMAIL OAUTH SETUP FOR EDITORIAL COMMAND CENTER")
    print(f"{'='*80}\n")

    # Ensure config directory exists
    CONFIG_DIR.mkdir(exist_ok=True)

    # Check credentials file
    if not check_credentials_file():
        sys.exit(1)

    # Run OAuth flow
    try:
        creds = run_oauth_flow()
    except Exception as e:
        print(f"\n❌ OAuth flow failed: {e}")
        sys.exit(1)

    # Test connection
    if not test_gmail_connection(creds):
        print(f"\n⚠️  Token created but connection test failed")
        print(f"   Token files may still work for extraction")

    # Print summary
    print_summary()

    print(f"\n✨ Gmail OAuth setup complete!")


if __name__ == "__main__":
    main()
