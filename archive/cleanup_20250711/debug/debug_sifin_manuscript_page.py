#!/usr/bin/env python3
"""
Debug SIFIN manuscript page to find ALL referee emails and document locations
"""

from journals.sifin import SIFIN
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import re

def debug_sifin_manuscript_page():
    """Debug SIFIN manuscript page structure to find all emails and documents"""
    print("=" * 60)
    print("DEBUGGING SIFIN MANUSCRIPT PAGE FOR EMAILS AND DOCUMENTS")
    print("=" * 60)
    
    sifin = SIFIN()
    sifin.setup_driver(headless=False)  # Use visible mode for debugging
    
    if not sifin.authenticate():
        print("Authentication failed")
        return
    
    try:
        # Navigate to first manuscript
        manuscripts = sifin.extract_manuscripts()
        if not manuscripts:
            print("No manuscripts found")
            return
        
        # Use first manuscript
        manuscript = manuscripts[0]
        manuscript_url = f"https://sifin.siam.org/{manuscript['url']}"
        print(f"Navigating to manuscript: {manuscript['id']}")
        print(f"URL: {manuscript_url}")
        
        sifin.driver.get(manuscript_url)
        time.sleep(3)
        
        # Save page source
        page_source = sifin.driver.page_source
        with open('sifin_manuscript_detail.html', 'w') as f:
            f.write(page_source)
        print("Saved page source to sifin_manuscript_detail.html")
        
        # Parse page
        soup = BeautifulSoup(page_source, 'html.parser')
        
        print("\n=== LOOKING FOR REFEREE EMAILS ===")
        
        # Find all email patterns in the page
                email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                emails_found = re.findall(email_pattern, page_source)
                print(f"All emails found in page source: {emails_found}")
                
                # Look for referee-related sections
                print("\n=== REFEREE SECTIONS ===")
                details_table = soup.find('table', {'id': 'ms_details_expanded'})
                if details_table:
                    for row in details_table.find_all('tr'):
                        th = row.find('th')
                        td = row.find('td')
                        if th and td:
                            label = th.get_text(strip=True)
                            if 'referee' in label.lower():
                                print(f"Found referee section: {label}")
                                print(f"Content: {td.get_text(strip=True)}")
                                
                                # Check for emails in this section
                                section_emails = re.findall(email_pattern, td.get_text())
                                if section_emails:
                                    print(f"  Emails in section: {section_emails}")
                                
                                # Check for links
                                links = td.find_all('a')
                                for link in links:
                                    href = link.get('href', '')
                                    text = link.get_text(strip=True)
                                    print(f"  Link: {text} -> {href}")
                
                print("\n=== MANUSCRIPT ITEMS SECTION ===")
                
                # Look for "Manuscript Items" section
                manuscript_items_found = False
                for row in details_table.find_all('tr'):
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        label = th.get_text(strip=True)
                        if 'manuscript' in label.lower() and 'item' in label.lower():
                            manuscript_items_found = True
                            print(f"Found manuscript items section: {label}")
                            print(f"Content: {td.get_text(strip=True)}")
                            
                            # Look for PDF links
                            pdf_links = td.find_all('a', href=lambda x: x and '.pdf' in x.lower())
                            for link in pdf_links:
                                href = link.get('href')
                                text = link.get_text(strip=True)
                                print(f"  PDF: {text} -> {href}")
                
                if not manuscript_items_found:
                    print("No 'Manuscript Items' section found, looking for document links...")
                    
                    # Look for any PDF links
                    all_pdf_links = soup.find_all('a', href=lambda x: x and '.pdf' in x.lower())
                    print(f"Found {len(all_pdf_links)} PDF links:")
                    for i, link in enumerate(all_pdf_links):
                        href = link.get('href')
                        text = link.get_text(strip=True)
                        print(f"  PDF {i+1}: {text} -> {href}")
                
                print("\n=== WORKFLOW TASKS SECTION ===")
                
                # Look for workflow tasks / Associate Editor Recommendation
                workflow_found = False
                for row in details_table.find_all('tr'):
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        label = th.get_text(strip=True)
                        content = td.get_text(strip=True)
                        
                        if ('workflow' in label.lower() or 'task' in label.lower() or 
                            'recommendation' in content.lower() or 'associate editor' in content.lower()):
                            workflow_found = True
                            print(f"Found workflow section: {label}")
                            print(f"Content: {content}")
                            
                            # Look for clickable elements
                            clickable_elements = td.find_all(['a', 'button', 'input'])
                            for elem in clickable_elements:
                                if elem.name == 'a':
                                    href = elem.get('href', '')
                                    text = elem.get_text(strip=True)
                                    print(f"  Clickable link: {text} -> {href}")
                                else:
                                    text = elem.get_text(strip=True)
                                    onclick = elem.get('onclick', '')
                                    print(f"  Clickable element: {text} (onclick: {onclick})")
                
                if not workflow_found:
                    print("No workflow tasks found, looking for any recommendation or review links...")
                    
                    # Look for any links containing review/recommendation keywords
                    review_links = soup.find_all('a', text=re.compile(r'(review|recommendation|report)', re.I))
                    for link in review_links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        print(f"  Review link: {text} -> {href}")
                
                # Look for any hidden or embedded emails
                print("\n=== HIDDEN EMAIL SEARCH ===")
                
                # Check all text content for emails
                all_text = soup.get_text()
                all_emails = re.findall(email_pattern, all_text)
                unique_emails = list(set(all_emails))
                
                print(f"All unique emails found on page: {unique_emails}")
                
                # Check for emails in script tags or hidden elements
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string:
                        script_emails = re.findall(email_pattern, script.string)
                        if script_emails:
                            print(f"Emails in script: {script_emails}")
                
                print("\n=== COMPLETE TABLE STRUCTURE ===")
                
                # Show complete table structure
                if details_table:
                    print("Complete manuscript details table:")
                    for i, row in enumerate(details_table.find_all('tr')):
                        th = row.find('th')
                        td = row.find('td')
                        if th and td:
                            label = th.get_text(strip=True)
                            content = td.get_text(strip=True)[:100] + ("..." if len(td.get_text(strip=True)) > 100 else "")
                            print(f"  Row {i+1}: {label} -> {content}")
                
                input("Press Enter to continue...")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            sifin.driver.quit()
        except:
            pass

if __name__ == "__main__":
    debug_sifin_manuscript_page()