#!/usr/bin/env python3
"""
GET ANY MOR VERIFICATION CODE - NO TIMESTAMP FILTERING
"""

import os
import json
import base64
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

print("="*80)
print("🔍 SEARCHING FOR ANY MOR VERIFICATION CODE IN GMAIL")
print("="*80)

# Load Gmail credentials
token_path = "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json"
print(f"\n📁 Loading token from: {token_path}")

with open(token_path, 'r') as f:
    token_data = json.load(f)

creds = Credentials.from_authorized_user_info(token_data, ['https://www.googleapis.com/auth/gmail.readonly'])

if creds and creds.expired and creds.refresh_token:
    print("   Refreshing expired token...")
    creds.refresh(Request())

service = build('gmail', 'v1', credentials=creds)
print("   ✅ Gmail service connected")

# Search for MOR verification emails - NO TIMESTAMP FILTER
query = 'from:onbehalfof@manuscriptcentral.com subject:"verification code"'
print(f"\n🔍 Query: {query}")

try:
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=10
    ).execute()

    messages = results.get('messages', [])
    print(f"\n📧 Found {len(messages)} matching emails")

    if not messages:
        print("   ❌ No MOR verification emails found at all!")
    else:
        # Process each message
        for i, msg in enumerate(messages[:5], 1):
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()

            # Get headers
            headers = msg_data['payload'].get('headers', [])
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Unknown')

            print(f"\n📧 Email {i}:")
            print(f"   Date: {date}")
            print(f"   Subject: {subject}")

            # Get body
            body = ""
            if 'parts' in msg_data['payload']:
                for part in msg_data['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
            elif msg_data['payload']['body'].get('data'):
                data = msg_data['payload']['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

            # Extract code
            code_match = re.search(r'\b(\d{6})\b', body)
            if code_match:
                code = code_match.group(1)
                print(f"   ✅ CODE FOUND: {code}")

                # Show snippet of body around code
                idx = body.find(code)
                snippet = body[max(0, idx-50):min(len(body), idx+50)]
                print(f"   Context: ...{snippet}...")
            else:
                print("   ❌ No 6-digit code found in body")
                print(f"   Body preview: {body[:200]}...")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("SEARCH COMPLETE")
print("="*80)