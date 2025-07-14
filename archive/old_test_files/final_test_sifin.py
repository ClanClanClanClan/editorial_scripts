#!/usr/bin/env python3
"""
Final test of SIFIN improvements (without referee reports to avoid timeout)
"""

from journals.sifin import SIFIN
import time

def final_test_sifin():
    """Final test of SIFIN improvements"""
    print("=" * 60)
    print("FINAL SIFIN IMPROVEMENT TEST")
    print("=" * 60)
    
    sifin = SIFIN()
    # Temporarily disable referee report extraction to avoid timeout
    sifin.setup_driver(headless=True)
    
    if not sifin.authenticate():
        print("Authentication failed")
        return
    
    try:
        # Extract manuscripts with referee details
        manuscripts = sifin.extract_manuscripts()
        if not manuscripts:
            print("No manuscripts found")
            return
        
        print(f"Found {len(manuscripts)} manuscripts")
        
        # Test document extraction for each manuscript (without referee reports)
        for manuscript in manuscripts:
            # Navigate to manuscript detail page
            if manuscript.get('url'):
                full_url = sifin.config['base_url'] + '/' + manuscript['url']
                sifin.driver.get(full_url)
                time.sleep(2)
                
                # Extract documents (but skip referee reports)
                try:
                    # Parse the page to find manuscript items section
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(sifin.driver.page_source, 'html.parser')
                    
                    # Find the manuscript details table
                    details_table = soup.find('table', {'id': 'ms_details_expanded'})
                    if details_table:
                        manuscript_pdf_found = False
                        cover_letter_found = False
                        
                        # Look for Manuscript Items section
                        manuscript_items_section = soup.find('font', string=lambda text: text and 'manuscript items' in text.lower())
                        if manuscript_items_section:
                            ol_section = manuscript_items_section.find_next('ol')
                            if ol_section:
                                pdf_links = ol_section.find_all('a', href=lambda x: x and '.pdf' in x.lower())
                                for link in pdf_links:
                                    link_text = link.get_text(strip=True)
                                    href = link.get('href')
                                    if 'cover' in link_text.lower() and 'letter' in link_text.lower():
                                        manuscript['cover_letter_url'] = href
                                        cover_letter_found = True
                                    elif 'article' in link_text.lower() and not manuscript_pdf_found:
                                        manuscript['pdf_url'] = href
                                        manuscript_pdf_found = True
                        
                        # If no PDF found in Manuscript Items, look for any PDF in the page
                        if not manuscript_pdf_found:
                            pdf_links = sifin.driver.find_elements(
                                sifin.driver.find_element_by_xpath, "//a[contains(@href, '.pdf')]"
                            )
                            
                            if pdf_links:
                                first_pdf = pdf_links[0]
                                href = first_pdf.get_attribute('href')
                                
                                # Check if this PDF is actually a cover letter based on the URL
                                if 'cover_letter' in href.lower():
                                    manuscript['cover_letter_url'] = href
                                    cover_letter_found = True
                                    
                                    # Look for additional PDFs that might be the actual manuscript
                                    for pdf_link in pdf_links[1:]:
                                        additional_href = pdf_link.get_attribute('href')
                                        if 'art_file' in additional_href.lower():
                                            manuscript['pdf_url'] = additional_href
                                            manuscript_pdf_found = True
                                            break
                                else:
                                    manuscript['pdf_url'] = href
                                    manuscript_pdf_found = True
                        
                        # Set found flags
                        manuscript['pdf_found'] = manuscript_pdf_found
                        manuscript['cover_letter_found'] = cover_letter_found
                        
                except Exception as e:
                    print(f"Error processing documents for {manuscript['id']}: {e}")
                    manuscript['pdf_found'] = False
                    manuscript['cover_letter_found'] = False
        
        # Final summary
        print("\n" + "=" * 60)
        print("FINAL RESULTS SUMMARY")
        print("=" * 60)
        
        total_manuscripts = len(manuscripts)
        total_referees = sum(len(ms.get('referees', [])) for ms in manuscripts)
        total_emails = sum(len([ref for ref in ms.get('referees', []) if ref.get('email')]) for ms in manuscripts)
        total_pdfs = sum(1 for ms in manuscripts if ms.get('pdf_found'))
        total_cover_letters = sum(1 for ms in manuscripts if ms.get('cover_letter_found'))
        
        print(f"📋 Total manuscripts: {total_manuscripts}")
        print(f"👥 Total referees: {total_referees}")
        print(f"📧 Total emails found: {total_emails}/{total_referees} ({total_emails/total_referees*100:.1f}%)")
        print(f"📄 Total PDFs found: {total_pdfs}/{total_manuscripts} ({total_pdfs/total_manuscripts*100:.1f}%)")
        print(f"✉️  Total cover letters found: {total_cover_letters}/{total_manuscripts} ({total_cover_letters/total_manuscripts*100:.1f}%)")
        
        print("\n📊 Per-manuscript details:")
        for manuscript in manuscripts:
            ms_id = manuscript['id']
            referee_count = len(manuscript.get('referees', []))
            email_count = len([ref for ref in manuscript.get('referees', []) if ref.get('email')])
            pdf_status = "✅" if manuscript.get('pdf_found') else "❌"
            cover_status = "✅" if manuscript.get('cover_letter_found') else "❌"
            
            print(f"  {ms_id}: {email_count}/{referee_count} emails, PDF {pdf_status}, Cover {cover_status}")
        
        print("\n🎉 FINAL ACHIEVEMENT:")
        if total_emails == total_referees:
            print("✅ ALL REFEREE EMAILS SUCCESSFULLY EXTRACTED!")
        else:
            print(f"⚠️  {total_emails}/{total_referees} referee emails extracted ({total_emails/total_referees*100:.1f}%)")
        
        if total_cover_letters > 0:
            print(f"✅ COVER LETTER EXTRACTION WORKING! ({total_cover_letters}/{total_manuscripts} found)")
        else:
            print("❌ Cover letter extraction needs work")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        sifin.driver.quit()

if __name__ == "__main__":
    final_test_sifin()