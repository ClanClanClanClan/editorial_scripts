#!/usr/bin/env python3
"""
Test SICON complete extraction with emails and PDFs
"""

from journals.sicon import SICON
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_sicon_complete():
    """Test SICON complete extraction in headless mode"""
    print("=" * 60)
    print("TESTING SICON COMPLETE EXTRACTION (HEADLESS)")
    print("=" * 60)
    
    try:
        # Create and setup SICON with HEADLESS mode
        sicon = SICON()
        sicon.setup_driver(headless=True)  # HEADLESS!
        
        print("\n1. Authenticating...")
        if not sicon.authenticate():
            print("❌ Authentication failed")
            return False
        
        print("\n2. Extracting manuscripts...")
        manuscripts = sicon.extract_manuscripts()
        
        if not manuscripts:
            print("❌ No manuscripts found")
            return False
        
        print(f"\n3. Analysis Results:")
        print(f"   Total manuscripts: {len(manuscripts)}")
        
        # Count emails and PDFs
        total_referees = 0
        emails_found = 0
        pdfs_found = 0
        
        for manuscript in manuscripts:
            # Count referees and emails
            manuscript_refs = len(manuscript.get('referees', []))
            total_referees += manuscript_refs
            
            for referee in manuscript.get('referees', []):
                if referee.get('email'):
                    emails_found += 1
            
            # Check PDF
            if manuscript.get('documents', {}).get('pdf'):
                pdfs_found += 1
        
        print(f"\n4. Detailed Results:")
        print(f"   📧 Emails: {emails_found}/{total_referees}")
        print(f"   📄 PDFs: {pdfs_found}/{len(manuscripts)}")
        
        # Show per-manuscript breakdown
        for i, manuscript in enumerate(manuscripts, 1):
            ms_id = manuscript.get('id', 'N/A')
            title = manuscript.get('title', 'N/A')[:40] + "..."
            
            # Count emails for this manuscript
            ms_emails = sum(1 for ref in manuscript.get('referees', []) if ref.get('email'))
            ms_total_refs = len(manuscript.get('referees', []))
            
            # Check PDF
            has_pdf = "✅" if manuscript.get('documents', {}).get('pdf') else "❌"
            
            print(f"\n   Manuscript {i}: {ms_id}")
            print(f"     Title: {title}")
            print(f"     Emails: {ms_emails}/{ms_total_refs}")
            print(f"     PDF: {has_pdf}")
            
            # Show referee details
            for referee in manuscript.get('referees', []):
                status = referee.get('status', 'Unknown')
                email = referee.get('email', 'NOT FOUND')
                name = referee.get('name', 'Unknown')
                print(f"       - {name} ({status}): {email}")
        
        # Final assessment
        print(f"\n5. Final Assessment:")
        
        # Email assessment
        if emails_found == total_referees:
            print("   ✅ EMAILS: Perfect - All referee emails found!")
            email_score = 3
        elif emails_found >= total_referees * 0.8:
            print(f"   ⚠️  EMAILS: Good - {emails_found}/{total_referees} emails found")
            email_score = 2
        elif emails_found > 0:
            print(f"   ⚠️  EMAILS: Partial - {emails_found}/{total_referees} emails found")
            email_score = 1
        else:
            print("   ❌ EMAILS: Failed - No emails found")
            email_score = 0
        
        # PDF assessment
        if pdfs_found == len(manuscripts):
            print("   ✅ PDFs: Perfect - All manuscript PDFs found!")
            pdf_score = 3
        elif pdfs_found >= len(manuscripts) * 0.8:
            print(f"   ⚠️  PDFs: Good - {pdfs_found}/{len(manuscripts)} PDFs found")
            pdf_score = 2
        elif pdfs_found > 0:
            print(f"   ⚠️  PDFs: Partial - {pdfs_found}/{len(manuscripts)} PDFs found")
            pdf_score = 1
        else:
            print("   ❌ PDFs: Failed - No PDFs found")
            pdf_score = 0
        
        # Overall score
        total_score = email_score + pdf_score
        max_score = 6
        
        print(f"\n6. Overall Score: {total_score}/{max_score}")
        
        if total_score >= 5:
            print("   🎉 SICON is nearly perfect!")
            return True
        elif total_score >= 3:
            print("   👍 SICON is mostly working")
            return False
        else:
            print("   🔧 SICON needs significant fixes")
            return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            sicon.driver.quit()
        except:
            pass

if __name__ == "__main__":
    success = test_sicon_complete()
    print(f"\nSICON Result: {'SUCCESS' if success else 'NEEDS FIXES'}")