#!/usr/bin/env python3
"""
Analyze the existing SICON extraction results
"""

import json

# Load the successful extraction
with open('sicon_extraction_20250714_102833.json', 'r') as f:
    data = json.load(f)

print("📊 ANALYSIS OF EXISTING SICON EXTRACTION")
print("=" * 50)

print(f"\nExtraction time: {data['extraction_time']}")
print(f"Total manuscripts: {data['total_manuscripts']}")

# Analyze referee distribution
all_statuses = {}
total_refs = 0

for ms in data['manuscripts']:
    print(f"\n📄 {ms['id']}: {ms['title'][:50]}...")
    refs = ms['referees']
    total_refs += len(refs)
    
    # Count statuses
    ms_statuses = {}
    for ref in refs:
        status = ref.get('status', 'Unknown')
        all_statuses[status] = all_statuses.get(status, 0) + 1
        ms_statuses[status] = ms_statuses.get(status, 0) + 1
    
    print(f"   Referees: {len(refs)}")
    for status, count in ms_statuses.items():
        print(f"   - {status}: {count}")

print(f"\n📈 OVERALL REFEREE ANALYSIS:")
print(f"Total referee entries: {total_refs}")
print("\nStatus distribution:")
for status, count in sorted(all_statuses.items()):
    print(f"  - {status}: {count}")

# Check for duplicates
print("\n🔍 Duplicate check:")
for ms in data['manuscripts']:
    emails = {}
    for ref in ms['referees']:
        email = ref.get('email', 'NO_EMAIL')
        emails[email] = emails.get(email, 0) + 1
    
    duplicates = {k: v for k, v in emails.items() if v > 1}
    if duplicates:
        print(f"\n{ms['id']} has duplicates:")
        for email, count in duplicates.items():
            print(f"  - {email}: appears {count} times")

print("\n⚠️  ISSUES FOUND:")
print(f"1. All referees show 'Review pending' or 'Suggested' status")
print(f"2. Total of {total_refs} referee entries (expected ~13 unique)")
print(f"3. No differentiation between declined/accepted/submitted")
print(f"4. Need to implement proper status parsing as discussed")