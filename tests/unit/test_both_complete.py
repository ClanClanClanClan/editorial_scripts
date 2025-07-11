#!/usr/bin/env python3
"""
Test complete extraction for both SICON and SIFIN
Check emails and PDFs are working
"""

from journals.sicon import SICON
from journals.sifin import SIFIN
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_journal_complete(journal_class, journal_name):
    """Test complete extraction for a journal"""
    print(f"\n{'='*80}")
    print(f"TESTING {journal_name} COMPLETE EXTRACTION")
    print(f"{'='*80}")
    
    try:
        # Create journal instance
        journal = journal_class()
        
        # Setup driver
        journal.setup_driver(headless=False)
        
        # Authenticate
        print(f"\n1. Authenticating with {journal_name}...")
        if not journal.authenticate():
            print(f"❌ {journal_name} Authentication failed")
            return False
        
        # Extract manuscripts
        print(f"\n2. Extracting manuscripts from {journal_name}...")
        manuscripts = journal.extract_manuscripts()
        
        # Analyze results
        print(f"\n3. {journal_name} Results Analysis:")
        print(f"   Total manuscripts: {len(manuscripts)}")
        
        total_referees = 0
        emails_found = 0
        pdfs_found = 0
        reports_found = 0
        
        for manuscript in manuscripts:
            manuscript_refs = len(manuscript.get('referees', []))
            total_referees += manuscript_refs
            
            # Check PDF
            if manuscript.get('documents', {}).get('pdf'):
                pdfs_found += 1
            
            # Check referee reports
            reports = manuscript.get('documents', {}).get('referee_reports', [])
            reports_found += len(reports)
            
            # Check referee emails
            for referee in manuscript.get('referees', []):
                if referee.get('email'):
                    emails_found += 1
        
        print(f"\n4. {journal_name} Summary:")
        print(f"   📄 Manuscripts: {len(manuscripts)}")
        print(f"   👥 Total referees: {total_referees}")
        print(f"   📧 Emails found: {emails_found}/{total_referees}")
        print(f"   📁 PDFs found: {pdfs_found}/{len(manuscripts)}")
        print(f"   📋 Reports found: {reports_found}")
        
        # Status breakdown
        status_counts = {}
        for manuscript in manuscripts:
            for referee in manuscript.get('referees', []):
                status = referee.get('status', 'Unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\n5. {journal_name} Status Breakdown:")
        for status, count in status_counts.items():
            print(f"   {status}: {count}")
        
        # Check completeness
        print(f"\n6. {journal_name} Completeness Assessment:")
        
        # Email completeness
        if emails_found == total_referees:
            print("   ✅ EMAIL EXTRACTION: Perfect - All referee emails found!")
        elif emails_found > 0:
            print(f"   ⚠️  EMAIL EXTRACTION: Partial - {emails_found}/{total_referees} emails found")
        else:
            print("   ❌ EMAIL EXTRACTION: Failed - No emails found")
        
        # PDF completeness
        if pdfs_found == len(manuscripts):
            print("   ✅ PDF EXTRACTION: Perfect - All manuscript PDFs found!")
        elif pdfs_found > 0:
            print(f"   ⚠️  PDF EXTRACTION: Partial - {pdfs_found}/{len(manuscripts)} PDFs found")
        else:
            print("   ❌ PDF EXTRACTION: Failed - No PDFs found")
        
        # Status clarity
        if 'Unknown' not in status_counts:
            print("   ✅ STATUS CLARITY: Perfect - No unknown statuses!")
        else:
            print(f"   ⚠️  STATUS CLARITY: {status_counts.get('Unknown', 0)} unknown statuses")
        
        # Overall assessment
        overall_score = 0
        if emails_found == total_referees: overall_score += 1
        if pdfs_found == len(manuscripts): overall_score += 1
        if 'Unknown' not in status_counts: overall_score += 1
        
        print(f"\n7. {journal_name} Overall Score: {overall_score}/3")
        if overall_score == 3:
            print(f"   🎉 {journal_name} is PERFECT!")
        elif overall_score >= 2:
            print(f"   👍 {journal_name} is mostly working, needs minor fixes")
        else:
            print(f"   🔧 {journal_name} needs significant fixes")
        
        return overall_score == 3
        
    except Exception as e:
        print(f"❌ {journal_name} ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            journal.driver.quit()
        except:
            pass

def main():
    """Test both journals"""
    print("COMPLETE EXTRACTION TEST FOR SICON AND SIFIN")
    print("="*80)
    
    # Test SICON
    sicon_perfect = test_journal_complete(SICON, "SICON")
    
    # Test SIFIN
    sifin_perfect = test_journal_complete(SIFIN, "SIFIN")
    
    # Final summary
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")
    
    print(f"SICON: {'✅ PERFECT' if sicon_perfect else '🔧 NEEDS FIXES'}")
    print(f"SIFIN: {'✅ PERFECT' if sifin_perfect else '🔧 NEEDS FIXES'}")
    
    if sicon_perfect and sifin_perfect:
        print("\n🎉 BOTH JOURNALS ARE PERFECT!")
        print("✅ All emails extracted")
        print("✅ All PDFs downloaded")
        print("✅ All statuses clear")
    else:
        print("\n🔧 FIXES NEEDED:")
        if not sicon_perfect:
            print("- SICON needs email/PDF extraction fixes")
        if not sifin_perfect:
            print("- SIFIN needs email/PDF extraction fixes")

if __name__ == "__main__":
    main()