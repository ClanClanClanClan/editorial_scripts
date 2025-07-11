#!/usr/bin/env python3
"""
Test SIFIN email extraction with fixes
"""

from journals.sifin import SIFIN
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_sifin_emails():
    """Test SIFIN email extraction"""
    
    print("=" * 60)
    print("TESTING SIFIN EMAIL EXTRACTION FIXES")
    print("=" * 60)
    
    try:
        # Create SIFIN instance
        sifin = SIFIN()
        
        # Run extraction
        print("\n1. Running SIFIN extraction...")
        
        # Setup driver first
        sifin.setup_driver(headless=False)  # Use visible mode for debugging
        
        # Then authenticate
        if not sifin.authenticate():
            print("❌ Authentication failed")
            return False
        
        # Then extract manuscripts
        manuscripts = sifin.extract_manuscripts()
        
        print(f"\n2. Results Summary:")
        print(f"   Total manuscripts: {len(manuscripts)}")
        
        total_referees = 0
        emails_found = 0
        
        for manuscript in manuscripts:
            manuscript_refs = len(manuscript.get('referees', []))
            total_referees += manuscript_refs
            
            for referee in manuscript.get('referees', []):
                if referee.get('email'):
                    emails_found += 1
        
        print(f"   Total referees: {total_referees}")
        print(f"   Emails found: {emails_found}")
        print(f"   Missing emails: {total_referees - emails_found}")
        
        # Show detailed results
        print(f"\n3. Detailed Results:")
        for i, manuscript in enumerate(manuscripts, 1):
            print(f"\nManuscript {i}: {manuscript.get('id', 'N/A')}")
            print(f"  Title: {manuscript.get('title', 'N/A')[:50]}...")
            print(f"  Referees: {len(manuscript.get('referees', []))}")
            
            for j, referee in enumerate(manuscript.get('referees', []), 1):
                email_status = "✅" if referee.get('email') else "❌"
                print(f"    {j}. {referee.get('name', 'N/A')} ({referee.get('status', 'N/A')}) {email_status}")
                if referee.get('email'):
                    print(f"       Email: {referee['email']}")
        
        # Final assessment
        print(f"\n4. Email Extraction Assessment:")
        if emails_found == total_referees:
            print("✅ SUCCESS: All referee emails extracted!")
        elif emails_found > 0:
            print(f"⚠️  PARTIAL: {emails_found}/{total_referees} emails extracted")
        else:
            print("❌ FAILED: No referee emails extracted")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_sifin_emails()