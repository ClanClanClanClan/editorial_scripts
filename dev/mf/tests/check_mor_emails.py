#!/usr/bin/env python3
"""
Check all MOR verification emails
"""

import sys
import time
import re

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

print("="*60)
print("📧 CHECKING MOR VERIFICATION EMAILS")
print("="*60)

# Gmail setup
token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')
with open(token_file, 'r') as f:
    creds = Credentials.from_authorized_user_info(json.load(f))

if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build('gmail', 'v1', credentials=creds)

# Get ALL MOR verification emails
print("\n1. Fetching all MOR verification emails...")
query = 'from:onbehalfof@manuscriptcentral.com subject:"Verification Code"'
results = service.users().messages().list(
    userId='me',
    q=query,
    maxResults=20
).execute()

messages = results.get('messages', [])
print(f"   Found {len(messages)} verification emails")

current_time = time.time()
codes = []

for i, msg in enumerate(messages, 1):
    msg_data = service.users().messages().get(
        userId='me',
        id=msg['id']
    ).execute()

    internal_date = int(msg_data.get('internalDate', 0)) // 1000
    age_minutes = (current_time - internal_date) / 60
    age_hours = age_minutes / 60

    # Get headers
    headers = msg_data['payload'].get('headers', [])
    date_header = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')

    # Get code
    snippet = msg_data.get('snippet', '')
    code_match = re.search(r'\b(\d{6})\b', snippet)

    if code_match:
        code = code_match.group(1)
        codes.append({
            'code': code,
            'age_hours': age_hours,
            'date': date_header,
            'snippet': snippet[:80]
        })

print(f"\n2. Verification codes by age:")
for i, code_info in enumerate(codes[:10], 1):
    print(f"\n   Email {i}:")
    print(f"      Code: {code_info['code']}")
    print(f"      Age: {code_info['age_hours']:.1f} hours")
    print(f"      Date: {code_info['date']}")

# Check if we can trigger a new email
print("\n3. Most recent codes:")
if codes:
    latest = codes[0]
    print(f"   Latest: {latest['code']} ({latest['age_hours']:.1f} hours old)")

    if latest['age_hours'] < 1:
        print("   ✅ Code is fresh enough to use!")
    elif latest['age_hours'] < 24:
        print("   ⚠️  Code might still work")
    else:
        print("   ❌ Code is too old")

print("\n4. Suggestion:")
if codes and codes[0]['age_hours'] < 1:
    print(f"   Use code: {codes[0]['code']}")
else:
    print("   Need to wait and retry later for a fresh email")
    print("   MOR may have rate limiting on verification emails")

print("\n" + "="*60)
print("CHECK COMPLETE")
print("="*60)