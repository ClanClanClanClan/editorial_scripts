#!/usr/bin/env python3
"""Debug FS-25-4725 referee extraction."""

import json
from fs_extractor import ComprehensiveFSExtractor

def debug_manuscript():
    """Debug why FS-25-4725 has no referees."""
    print("🔍 DEBUGGING FS-25-4725 REFEREE EXTRACTION")
    print("=" * 60)
    
    extractor = ComprehensiveFSExtractor()
    
    # Initialize Gmail
    if not extractor.setup_gmail_service():
        print("❌ Failed to initialize Gmail")
        return
    
    # Get emails for FS-25-4725
    test_id = "FS-25-4725"
    query = f'"{test_id}"'
    emails = extractor.search_emails(query, max_results=50)
    
    print(f"📧 Found {len(emails)} emails for {test_id}")
    print("\n" + "=" * 60)
    print("EMAIL ANALYSIS:")
    print("=" * 60)
    
    # Analyze each email
    for i, email in enumerate(emails):
        # Get email metadata
        headers = email['payload'].get('headers', [])
        subject = ''
        sender = ''
        date = ''
        
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
            elif header['name'] == 'From':
                sender = header['value']
            elif header['name'] == 'Date':
                date = header['value']
        
        print(f"\n📧 EMAIL {i+1}:")
        print(f"   Date: {date[:30]}")
        print(f"   From: {sender}")
        print(f"   Subject: {subject}")
        
        # Get email body
        body = extractor.get_email_body(email['payload'])
        
        # Look for referee mentions
        if body:
            body_lower = body.lower()
            
            # Check for referee keywords
            referee_keywords = ['referee', 'reviewer', 'review', 'invitation', 'accept', 'decline', 'agreed']
            found_keywords = [k for k in referee_keywords if k in body_lower]
            
            if found_keywords:
                print(f"   🔍 Keywords found: {', '.join(found_keywords)}")
                
                # Extract potential referee names
                import re
                
                # Look for names after specific patterns
                patterns = [
                    r'invited\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
                    r'asked\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+(?:has\s+)?(?:accepted|agreed|declined)',
                    r'referee[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
                    r'(?:Prof(?:essor)?|Dr)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
                ]
                
                found_names = set()
                for pattern in patterns:
                    matches = re.findall(pattern, body, re.IGNORECASE)
                    for match in matches:
                        name = match.strip() if isinstance(match, str) else match
                        if name and len(name.split()) >= 2:
                            # Skip known editors
                            if not any(ed in name for ed in ['Schweizer', 'Possamai', 'Dylan', 'Zhou']):
                                found_names.add(name)
                
                if found_names:
                    print(f"   👤 Potential referees found: {', '.join(found_names)}")
                
                # Show relevant snippet
                for line in body.split('\n'):
                    line_lower = line.lower()
                    if any(k in line_lower for k in ['referee', 'reviewer', 'invited', 'accept', 'agreed']):
                        print(f"   📝 Relevant line: {line[:100]}...")
        
        # Check attachments
        attachments = extractor.get_email_attachments(email)
        if attachments:
            print(f"   📎 Attachments: {[a['filename'] for a in attachments]}")
    
    print("\n" + "=" * 60)
    print("RUNNING FULL EXTRACTION FOR FS-25-4725:")
    print("=" * 60)
    
    # Build timeline with debug output
    manuscript = extractor.build_manuscript_timeline(test_id, emails, is_current=True)
    
    print(f"\nRESULTS:")
    print(f"Title: {manuscript['title'][:50]}...")
    print(f"Status: {manuscript['status']}")
    print(f"Referees found: {len(manuscript['referees'])}")
    
    for ref in manuscript['referees']:
        print(f"\n👤 {ref['name']}")
        print(f"   Email: {ref.get('email', 'Not found')}")
        print(f"   Institution: {ref.get('institution', 'Unknown')}")
        print(f"   Response: {ref.get('response', 'Unknown')}")
    
    # Save debug output
    with open('debug_fs_4725.json', 'w') as f:
        json.dump({
            'manuscript_id': test_id,
            'email_count': len(emails),
            'extraction_result': manuscript
        }, f, indent=2, default=str)
    print("\n💾 Debug output saved to debug_fs_4725.json")

if __name__ == '__main__':
    debug_manuscript()