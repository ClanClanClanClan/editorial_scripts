#!/usr/bin/env python3
"""Test FS referee extraction for a single manuscript."""

import json
from fs_extractor import ComprehensiveFSExtractor

def test_single_manuscript():
    """Test referee extraction on a single manuscript."""
    print("🧪 TESTING FS REFEREE EXTRACTION - SINGLE MANUSCRIPT")
    print("=" * 60)
    
    extractor = ComprehensiveFSExtractor()
    
    # Initialize Gmail
    if not extractor.setup_gmail_service():
        print("❌ Failed to initialize Gmail")
        return
    
    # Pick a specific manuscript to test
    test_id = "FS-25-4733"  # Current manuscript
    
    print(f"\n📄 Testing manuscript: {test_id}")
    
    # Get emails for this manuscript
    query = f'"{test_id}"'
    emails = extractor.search_emails(query, max_results=50)
    
    print(f"📧 Found {len(emails)} emails")
    
    # Build timeline
    manuscript = extractor.build_manuscript_timeline(test_id, emails, is_current=True)
    
    # Show results
    print(f"\n📊 EXTRACTION RESULTS:")
    print(f"Title: {manuscript['title'][:50]}...")
    print(f"Status: {manuscript['status']}")
    print(f"Editor: {manuscript.get('editor', 'Unknown')}")
    
    # Show referees
    referees = manuscript['referees']
    print(f"\n🧑‍⚖️ REFEREES FOUND: {len(referees)}")
    
    for referee_data in referees:
        name = referee_data.get('name', 'Unknown')
        print(f"\n  📋 {name}")
        print(f"     Email: {referee_data.get('email', 'Not found')}")
        print(f"     Institution: {referee_data.get('institution', 'Unknown')}")
        print(f"     Response: {referee_data.get('response', 'Unknown')}")
        print(f"     Report submitted: {referee_data.get('report_submitted', False)}")
        
        if referee_data.get('report_submitted'):
            print(f"     Report date: {referee_data.get('report_date', 'Unknown')}")
    
    # Show reports
    reports = manuscript['referee_reports']
    print(f"\n📄 REPORTS FOUND: {len(reports)}")
    
    for report in reports:
        print(f"\n  📎 {report['filename']}")
        print(f"     Date: {report['date']}")
        print(f"     From: {report['from'][:50]}...")
        print(f"     Matched to: {report.get('referee', 'Unknown')}")
    
    # Show timeline events
    print(f"\n⏰ TIMELINE EVENTS: {len(manuscript['timeline'])}")
    
    for event in manuscript['timeline'][:10]:  # Show first 10 events
        print(f"\n  {event['date'][:10]} - {event['type']}")
        print(f"     Subject: {event['subject'][:50]}...")
        print(f"     From: {event['from'][:50]}...")
        
        if event['details']:
            for key, value in event['details'].items():
                print(f"     {key}: {value}")
    
    # Save detailed output
    with open('test_fs_referee_results.json', 'w') as f:
        json.dump(manuscript, f, indent=2, default=str)
    print("\n💾 Detailed results saved to test_fs_referee_results.json")

if __name__ == '__main__':
    test_single_manuscript()