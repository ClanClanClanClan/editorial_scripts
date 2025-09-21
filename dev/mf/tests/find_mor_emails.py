#!/usr/bin/env python3
"""
Find MOR emails with correct sender
"""

import sys
import json
import time
import re
from pathlib import Path

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

print("="*60)
print("🔍 FINDING MOR EMAILS")
print("="*60)

# Load token
token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')
with open(token_file, 'r') as f:
    creds = Credentials.from_authorized_user_info(json.load(f))

if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build('gmail', 'v1', credentials=creds)

# Test different search queries
queries = [
    'from:manuscriptcentral-noreply@clarivate.com',
    'from:onbehalfof@manuscriptcentral.com',
    'from:ScholarOne',
    'subject:"Mathematics of Operations Research"',
    'subject:"Verification Code"',
    'Mathematics of Operations Research Verification',
    'MOR Verification'
]

print("\nTesting different search queries:")
for query in queries:
    print(f"\n   Query: {query}")
    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=5
        ).execute()

        messages = results.get('messages', [])
        print(f"   Results: {len(messages)} messages")

        if messages:
            # Check first message
            msg_data = service.users().messages().get(
                userId='me',
                id=messages[0]['id']
            ).execute()

            # Get headers
            headers = msg_data['payload'].get('headers', [])
            from_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Unknown')
            date_header = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')

            # Get snippet and look for code
            snippet = msg_data.get('snippet', '')
            code_match = re.search(r'\b(\d{6})\b', snippet)

            print(f"      Latest email:")
            print(f"         Date: {date_header}")
            print(f"         From: {from_header}")
            print(f"         Subject: {subject[:50]}...")
            if code_match:
                print(f"         ✅ Code found: {code_match.group(1)}")

    except Exception as e:
        print(f"   Error: {e}")

# Now find the most recent MOR verification email
print("\n" + "="*40)
print("\n📧 MOST RECENT MOR VERIFICATION EMAIL:")

query = 'subject:"Mathematics of Operations Research" subject:"Verification Code"'
try:
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=1
    ).execute()

    messages = results.get('messages', [])
    if messages:
        msg_data = service.users().messages().get(
            userId='me',
            id=messages[0]['id'],
            format='full'
        ).execute()

        # Extract all details
        headers = msg_data['payload'].get('headers', [])
        from_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Unknown')
        date_header = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')

        # Get body
        snippet = msg_data.get('snippet', '')

        # Get full body if available
        body = ''
        if 'parts' in msg_data['payload']:
            for part in msg_data['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = part['body'].get('data', '')
                    if body:
                        import base64
                        body = base64.urlsafe_b64decode(body).decode('utf-8')
                        break

        # Extract code from snippet or body
        text_to_search = body if body else snippet
        code_match = re.search(r'\b(\d{6})\b', text_to_search)

        print(f"   From: {from_header}")
        print(f"   Subject: {subject}")
        print(f"   Date: {date_header}")
        print(f"   Internal Date: {msg_data.get('internalDate', 'Unknown')}")
        print(f"   Message ID: {messages[0]['id']}")

        if code_match:
            print(f"\n   ✅ VERIFICATION CODE: {code_match.group(1)}")
        else:
            print(f"\n   ❌ No code found")
            print(f"   Snippet: {snippet[:200]}...")

        # Check if unread
        labels = msg_data.get('labelIds', [])
        if 'UNREAD' in labels:
            print(f"   Status: UNREAD")
        else:
            print(f"   Status: READ")

    else:
        print("   No MOR verification emails found")

except Exception as e:
    print(f"   Error: {e}")

print("\n" + "="*60)
print("SEARCH COMPLETE")
print("="*60)