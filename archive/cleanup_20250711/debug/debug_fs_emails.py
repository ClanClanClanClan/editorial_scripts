#!/usr/bin/env python3
"""
Debug FS journal email parsing to understand data structure
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from journals.fs import FSJournal

def debug_fs_emails():
    """Debug FS journal email parsing"""
    print("Debugging FS journal email parsing...")
    
    try:
        # Create FS journal instance
        fs_journal = FSJournal(driver=None)
        
        # Get the raw email data
        print("Fetching starred emails...")
        starred_emails = fs_journal.get_starred_emails()
        
        print(f"Found {len(starred_emails)} starred emails")
        
        # Show sample emails
        for i, email in enumerate(starred_emails[:3]):
            print(f"\n--- EMAIL {i+1} ---")
            print(f"Subject: {email.get('subject', 'No subject')}")
            print(f"From: {email.get('from', 'No from')}")
            print(f"To: {email.get('to', 'No to')}")
            print(f"Date: {email.get('date', 'No date')}")
            
            # Check if there's a body
            if email.get('body'):
                body = email['body'][:500]  # First 500 chars
                print(f"Body preview: {body}...")
            
            # Check for attachments
            if email.get('gmail_msg'):
                print("Has Gmail message object")
            
        print(f"\n--- PROCESSING EMAILS ---")
        
        # Run the actual parsing
        manuscripts = fs_journal.scrape_manuscripts_and_emails()
        
        print(f"Parsed {len(manuscripts)} manuscripts:")
        for i, ms in enumerate(manuscripts):
            print(f"\nManuscript {i+1}:")
            print(f"  ID: {ms.get('Manuscript #', 'No ID')}")
            print(f"  Title: {ms.get('Title', 'No title')}")
            print(f"  Contact Author: {ms.get('Contact Author', 'No author')}")
            print(f"  Current Stage: {ms.get('Current Stage', 'No stage')}")
            print(f"  Referees: {len(ms.get('Referees', []))}")
            
            # Debug referee data
            for j, ref in enumerate(ms.get('Referees', [])[:2]):
                print(f"    Referee {j+1}: {ref.get('Referee Name', 'No name')} ({ref.get('Status', 'No status')})")
        
        return True
        
    except Exception as e:
        print(f"❌ FS debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = debug_fs_emails()
    if success:
        print("\n✅ FS email debug completed")
    else:
        print("\n❌ FS email debug failed")
        sys.exit(1)