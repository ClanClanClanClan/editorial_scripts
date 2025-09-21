#!/usr/bin/env python3
"""
THOROUGH Gmail Debug - Check everything
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
print("🔍 THOROUGH GMAIL DEBUG")
print("="*60)

# Gmail setup
token_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json')
with open(token_file, 'r') as f:
    creds = Credentials.from_authorized_user_info(json.load(f))

if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build('gmail', 'v1', credentials=creds)

current_time = int(time.time())
print(f"\nCurrent timestamp: {current_time}")
print(f"Current time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))}")

# Test 1: Get ALL recent emails
print("\n1. Getting ALL recent emails (no filter)...")
all_results = service.users().messages().list(
    userId='me',
    maxResults=20
).execute()

all_messages = all_results.get('messages', [])
print(f"   Found {len(all_messages)} total recent emails")

# Test 2: Check different sender addresses
print("\n2. Testing different sender addresses...")
senders_to_test = [
    'from:onbehalfof@manuscriptcentral.com',
    'from:manuscriptcentral.com',
    'from:scholarone',
    'from:clarivate.com',
    'from:no-reply@manuscriptcentral.com',
    'from:support@manuscriptcentral.com'
]

for sender in senders_to_test:
    results = service.users().messages().list(
        userId='me',
        q=sender,
        maxResults=5
    ).execute()
    count = len(results.get('messages', []))
    print(f"   {sender}: {count} emails")

# Test 3: Search by subject
print("\n3. Testing subject searches...")
subjects = [
    'subject:"Verification Code"',
    'subject:"verification"',
    'subject:"Mathematics of Operations Research"',
    'subject:"MOR"',
    'subject:"login"',
    'subject:"security"'
]

for subject in subjects:
    results = service.users().messages().list(
        userId='me',
        q=subject,
        maxResults=5
    ).execute()
    count = len(results.get('messages', []))
    print(f"   {subject}: {count} emails")

# Test 4: Check emails from last hour
print("\n4. Checking emails from last hour...")
one_hour_ago = current_time - 3600
query = f'after:{one_hour_ago}'
results = service.users().messages().list(
    userId='me',
    q=query,
    maxResults=20
).execute()

recent_messages = results.get('messages', [])
print(f"   Found {len(recent_messages)} emails in last hour")

if recent_messages:
    print("\n   Recent emails:")
    for i, msg in enumerate(recent_messages[:10], 1):
        msg_data = service.users().messages().get(
            userId='me',
            id=msg['id']
        ).execute()

        headers = msg_data['payload'].get('headers', [])
        from_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Unknown')

        print(f"   {i}. From: {from_header[:40]}...")
        print(f"      Subject: {subject[:40]}...")

# Test 5: Check UNREAD emails
print("\n5. Checking UNREAD emails...")
unread_results = service.users().messages().list(
    userId='me',
    q='is:unread',
    maxResults=20
).execute()

unread_messages = unread_results.get('messages', [])
print(f"   Found {len(unread_messages)} unread emails")

# Look for MOR-related unread
mor_unread = service.users().messages().list(
    userId='me',
    q='is:unread from:manuscriptcentral.com',
    maxResults=10
).execute()

mor_unread_count = len(mor_unread.get('messages', []))
print(f"   MOR-related unread: {mor_unread_count}")

# Test 6: Check SPAM folder
print("\n6. Checking SPAM folder...")
spam_results = service.users().messages().list(
    userId='me',
    q='in:spam',
    maxResults=20
).execute()

spam_messages = spam_results.get('messages', [])
print(f"   Found {len(spam_messages)} emails in spam")

# Check for MOR in spam
mor_spam = service.users().messages().list(
    userId='me',
    q='in:spam manuscriptcentral',
    maxResults=10
).execute()

mor_spam_count = len(mor_spam.get('messages', []))
print(f"   MOR-related in spam: {mor_spam_count}")

# Test 7: Get labels to see all folders
print("\n7. Checking all labels/folders...")
labels = service.users().labels().list(userId='me').execute()
label_list = labels.get('labels', [])
print(f"   Found {len(label_list)} labels")

# Test 8: Search without any time restriction
print("\n8. All MOR emails ever (no time filter)...")
all_mor = service.users().messages().list(
    userId='me',
    q='from:onbehalfof@manuscriptcentral.com',
    maxResults=100
).execute()

all_mor_messages = all_mor.get('messages', [])
print(f"   Total MOR emails found: {len(all_mor_messages)}")

if all_mor_messages:
    # Get timestamps of recent ones
    print("\n   Checking timestamps of recent MOR emails:")
    for i, msg in enumerate(all_mor_messages[:10], 1):
        msg_data = service.users().messages().get(
            userId='me',
            id=msg['id']
        ).execute()

        internal_date = int(msg_data.get('internalDate', 0)) // 1000
        age_hours = (current_time - internal_date) / 3600

        snippet = msg_data.get('snippet', '')[:50]

        print(f"   {i}. Age: {age_hours:.1f} hours")
        print(f"      Time: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(internal_date))}")
        print(f"      Snippet: {snippet}...")

        # Look for verification code
        code_match = re.search(r'\b(\d{6})\b', msg_data.get('snippet', ''))
        if code_match:
            print(f"      Code: {code_match.group(1)}")

# Test 9: Try broader search
print("\n9. Broader search for ANY verification email...")
broad_query = 'verification OR code OR login OR "two factor" OR 2FA'
broad_results = service.users().messages().list(
    userId='me',
    q=f'{broad_query} after:{current_time - 7200}',  # Last 2 hours
    maxResults=20
).execute()

broad_messages = broad_results.get('messages', [])
print(f"   Found {len(broad_messages)} potential verification emails in last 2 hours")

if broad_messages:
    for i, msg in enumerate(broad_messages[:5], 1):
        msg_data = service.users().messages().get(
            userId='me',
            id=msg['id']
        ).execute()

        headers = msg_data['payload'].get('headers', [])
        from_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Unknown')

        print(f"   {i}. From: {from_header[:50]}...")
        print(f"      Subject: {subject[:50]}...")

print("\n" + "="*60)
print("THOROUGH DEBUG COMPLETE")
print("="*60)