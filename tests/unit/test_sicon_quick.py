#!/usr/bin/env python3
"""
Quick test of SICON email extraction
"""

from journals.sicon import SICON
import time

def test_sicon_quick():
    """Test SICON email extraction quickly"""
    print("=" * 60)
    print("QUICK SICON EMAIL EXTRACTION TEST")
    print("=" * 60)
    
    sicon = SICON()
    sicon.setup_driver(headless=True)
    
    if not sicon.authenticate():
        print("Authentication failed")
        return
    
    try:
        # Extract manuscripts
        manuscripts = sicon.extract_manuscripts()
        if not manuscripts:
            print("No manuscripts found")
            return
        
        print(f"Found {len(manuscripts)} manuscripts")
        
        # Test just the first manuscript
        manuscript = manuscripts[0]
        print(f"\nTesting {manuscript['id']}")
        
        # Get referee count
        referee_count = len(manuscript.get('referees', []))
        email_count = sum(1 for ref in manuscript.get('referees', []) if ref.get('email'))
        
        print(f"Referees: {referee_count}")
        print(f"Emails found: {email_count}")
        
        # Show details
        for ref in manuscript.get('referees', []):
            status = ref.get('status', 'Unknown')
            email = ref.get('email', 'NOT FOUND')
            print(f"  {ref['name']}: {status} -> {email}")
        
        # Summary
        if email_count == referee_count:
            print("✅ All emails found!")
        else:
            print(f"⚠️  Missing {referee_count - email_count} emails")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        sicon.driver.quit()

if __name__ == "__main__":
    test_sicon_quick()