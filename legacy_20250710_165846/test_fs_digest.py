#!/usr/bin/env python3
"""
Generate FS journal digest for testing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from journals.fs import FSJournal
from core.digest_utils import build_html_digest
from core.email_utils import fetch_starred_emails, robust_match_email_for_referee_fs

def generate_fs_digest():
    """Generate FS digest HTML"""
    print("Generating FS digest...")
    
    # Create FS journal
    fs_journal = FSJournal(driver=None)
    
    # Scrape manuscripts
    manuscripts = fs_journal.scrape_manuscripts_and_emails()
    
    # Fetch starred emails for crosscheck
    flagged_emails = fetch_starred_emails('FS')
    
    # Build digest
    manuscript_data = {'FS': manuscripts}
    unmatched_refs = {}
    urgent_refs = {}
    error_journals = {}
    
    # Generate HTML digest
    html_digest = build_html_digest(
        manuscript_data,
        error_journals,
        flagged_emails,
        unmatched_refs,
        urgent_refs,
        robust_match_email_for_referee_fs
    )
    
    # Save to file
    with open('fs_digest_test.html', 'w') as f:
        f.write(html_digest)
    
    print("Digest saved to fs_digest_test.html")
    
    # Also print summary
    print(f"\nFound {len(manuscripts)} manuscripts:")
    for ms in manuscripts:
        print(f"\n{ms['Manuscript #']}:")
        print(f"  Title: {ms['Title']}")
        print(f"  Author: {ms['Contact Author']}")
        print(f"  Stage: {ms['Current Stage']}")
        print(f"  Referees: {len(ms['Referees'])}")
        for ref in ms['Referees']:
            print(f"    - {ref['Referee Name']}: {ref['Status']} ({ref['Referee Email']})")
            if ref['Status'] == 'Accepted':
                print(f"      Accepted: {ref['Accepted Date']}, Due: {ref['Due Date']}")

if __name__ == "__main__":
    generate_fs_digest()