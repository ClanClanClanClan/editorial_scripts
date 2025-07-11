#!/usr/bin/env python3
"""
Test referee report extraction from SIFIN manuscripts
"""

from journals.sifin import SIFIN
import time

def test_referee_report_extraction():
    """Test referee report extraction from SIFIN manuscripts"""
    print("=" * 60)
    print("TESTING SIFIN REFEREE REPORT EXTRACTION")
    print("=" * 60)
    
    sifin = SIFIN()
    sifin.setup_driver(headless=True)
    
    if not sifin.authenticate():
        print("Authentication failed")
        return
    
    try:
        # Extract manuscripts
        manuscripts = sifin.extract_manuscripts()
        if not manuscripts:
            print("No manuscripts found")
            return
        
        print(f"Found {len(manuscripts)} manuscripts")
        
        # Test referee report extraction for each manuscript
        for manuscript in manuscripts:
            print(f"\n--- Testing {manuscript['id']} ---")
            
            # Navigate to manuscript detail page
            if manuscript.get('url'):
                full_url = sifin.config['base_url'] + '/' + manuscript['url']
                sifin.driver.get(full_url)
                time.sleep(2)
                
                # Extract documents including referee reports
                sifin._download_sifin_documents(manuscript)
                
                # Check results
                pdf_found = bool(manuscript.get('pdf_url'))
                cover_letter_found = bool(manuscript.get('cover_letter_url'))
                reports_found = len(manuscript['documents'].get('referee_reports', []))
                
                print(f"  PDF: {'✅' if pdf_found else '❌'}")
                print(f"  Cover Letter: {'✅' if cover_letter_found else '❌'}")
                print(f"  Referee Reports: {reports_found}")
                
                if reports_found > 0:
                    for i, report in enumerate(manuscript['documents']['referee_reports']):
                        print(f"    Report {i+1}: {report['source']} -> {report['url']}")
        
        # Summary
        total_reports = sum(len(ms['documents'].get('referee_reports', [])) for ms in manuscripts)
        
        print(f"\n=== SUMMARY ===")
        print(f"Total manuscripts: {len(manuscripts)}")
        print(f"Total referee reports found: {total_reports}")
        
        if total_reports > 0:
            print("🎉 Referee report extraction working!")
        else:
            print("⚠️  No referee reports found")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        sifin.driver.quit()

if __name__ == "__main__":
    test_referee_report_extraction()