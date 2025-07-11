#!/usr/bin/env python3
"""
Test cover letter extraction from SIFIN manuscripts
"""

from journals.sifin import SIFIN
import time

def test_cover_letter_extraction():
    """Test cover letter extraction from SIFIN manuscripts"""
    print("=" * 60)
    print("TESTING SIFIN COVER LETTER EXTRACTION")
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
        
        # Test cover letter extraction for each manuscript
        for manuscript in manuscripts:
            print(f"\n--- Testing {manuscript['id']} ---")
            
            # Navigate to manuscript detail page
            if manuscript.get('url'):
                full_url = sifin.config['base_url'] + '/' + manuscript['url']
                sifin.driver.get(full_url)
                time.sleep(2)
                
                # Extract documents
                sifin._download_sifin_documents(manuscript)
                
                # Check results
                pdf_found = bool(manuscript.get('pdf_url'))
                cover_letter_found = bool(manuscript.get('cover_letter_url'))
                
                print(f"  PDF: {'✅' if pdf_found else '❌'}")
                print(f"  Cover Letter: {'✅' if cover_letter_found else '❌'}")
                
                if pdf_found:
                    print(f"    PDF URL: {manuscript['pdf_url']}")
                if cover_letter_found:
                    print(f"    Cover Letter URL: {manuscript['cover_letter_url']}")
        
        # Summary
        total_pdfs = sum(1 for ms in manuscripts if ms.get('pdf_url'))
        total_cover_letters = sum(1 for ms in manuscripts if ms.get('cover_letter_url'))
        
        print(f"\n=== SUMMARY ===")
        print(f"Total manuscripts: {len(manuscripts)}")
        print(f"PDFs found: {total_pdfs}/{len(manuscripts)}")
        print(f"Cover letters found: {total_cover_letters}/{len(manuscripts)}")
        
        if total_cover_letters > 0:
            print("🎉 Cover letter extraction working!")
        else:
            print("⚠️  No cover letters found")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        sifin.driver.quit()

if __name__ == "__main__":
    test_cover_letter_extraction()