#!/usr/bin/env python3
"""
BASIC Gmail API connectivity test
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

print("="*60)
print("🔍 BASIC GMAIL API TEST")
print("="*60)

# Test 1: Can we even import the libraries?
print("\n1. Importing Gmail libraries...")
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    print("   ✅ Libraries imported")
except Exception as e:
    print(f"   ❌ Failed to import: {e}")
    sys.exit(1)

# Test 2: Can we load the token?
print("\n2. Loading token file...")
token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')

if not token_file.exists():
    print(f"   ❌ Token file not found: {token_file}")
    sys.exit(1)

try:
    with open(token_file, 'r') as f:
        token_data = json.load(f)
    print("   ✅ Token file loaded")
    print(f"   Token keys: {list(token_data.keys())}")
except Exception as e:
    print(f"   ❌ Failed to load token: {e}")
    sys.exit(1)

# Test 3: Can we create credentials?
print("\n3. Creating credentials...")
try:
    creds = Credentials.from_authorized_user_info(token_data)
    print("   ✅ Credentials created")
    print(f"   Token valid: {creds.valid}")
    print(f"   Token expired: {creds.expired}")
    print(f"   Has refresh token: {creds.refresh_token is not None}")
except Exception as e:
    print(f"   ❌ Failed to create credentials: {e}")
    sys.exit(1)

# Test 4: Can we refresh if expired?
if creds.expired and creds.refresh_token:
    print("\n4. Token expired, refreshing...")
    try:
        creds.refresh(Request())
        print("   ✅ Token refreshed")

        # Save refreshed token
        with open(token_file, 'w') as f:
            f.write(creds.to_json())
        print("   ✅ Refreshed token saved")
    except Exception as e:
        print(f"   ❌ Failed to refresh: {e}")
        sys.exit(1)
else:
    print("\n4. Token is valid, no refresh needed")

# Test 5: Can we build the Gmail service?
print("\n5. Building Gmail service...")
try:
    service = build('gmail', 'v1', credentials=creds)
    print("   ✅ Service built")
except Exception as e:
    print(f"   ❌ Failed to build service: {e}")
    sys.exit(1)

# Test 6: Can we access the user's profile?
print("\n6. Testing API access - Getting user profile...")
try:
    profile = service.users().getProfile(userId='me').execute()
    print("   ✅ API access successful!")
    print(f"   Email address: {profile.get('emailAddress', 'N/A')}")
    print(f"   Messages total: {profile.get('messagesTotal', 'N/A')}")
    print(f"   Threads total: {profile.get('threadsTotal', 'N/A')}")
except HttpError as e:
    print(f"   ❌ API Error: {e}")
    print(f"   Status code: {e.resp.status}")
    print(f"   Reason: {e.error_details}")
    sys.exit(1)
except Exception as e:
    print(f"   ❌ Failed to access API: {e}")
    sys.exit(1)

# Test 7: Can we list messages?
print("\n7. Listing recent messages...")
try:
    # Get ANY messages
    results = service.users().messages().list(
        userId='me',
        maxResults=10
    ).execute()

    messages = results.get('messages', [])
    print(f"   ✅ Found {len(messages)} messages")

    if messages:
        # Get details of first message
        msg = service.users().messages().get(
            userId='me',
            id=messages[0]['id']
        ).execute()

        # Extract basic info
        headers = msg['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
        from_addr = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')

        print(f"\n   First message:")
        print(f"      From: {from_addr[:50]}...")
        print(f"      Subject: {subject[:50]}...")

except Exception as e:
    print(f"   ❌ Failed to list messages: {e}")

# Test 8: Can we search for MOR emails specifically?
print("\n8. Searching for MOR emails...")
try:
    # Search for MOR emails
    query = 'from:manuscriptcentral-noreply@clarivate.com'
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=10
    ).execute()

    messages = results.get('messages', [])
    print(f"   ✅ Found {len(messages)} MOR emails")

    if messages:
        # Check first MOR email
        msg = service.users().messages().get(
            userId='me',
            id=messages[0]['id']
        ).execute()

        snippet = msg.get('snippet', '')
        internal_date = int(msg.get('internalDate', 0)) // 1000

        import time
        print(f"\n   Most recent MOR email:")
        print(f"      Date: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(internal_date))}")
        print(f"      Snippet: {snippet[:100]}...")

        # Look for verification code
        import re
        code_match = re.search(r'\b(\d{6})\b', snippet)
        if code_match:
            print(f"      ✅ Contains code: {code_match.group(1)}")
        else:
            print(f"      No 6-digit code found in snippet")

except Exception as e:
    print(f"   ❌ Failed to search: {e}")

print("\n" + "="*60)
print("✅ GMAIL API TEST COMPLETE")
print("="*60)