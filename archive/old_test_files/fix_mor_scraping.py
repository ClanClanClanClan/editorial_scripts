#!/usr/bin/env python3

"""
Fix MOR scraping to find all 6 referees.
The issue seems to be that we're not properly navigating to all manuscript queues.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from journals.mor import MORJournal
import time
import re
from bs4 import BeautifulSoup

def scrape_all_mor_manuscripts(driver, mor_journal, flagged_emails):
    """
    Comprehensively scrape ALL manuscripts and referees from MOR.
    Should find 6 referees total.
    """
    manuscripts = {}
    
    # First, make sure we're on the AE dashboard
    print("Ensuring we're on AE dashboard...")
    
    # Look for the Associate Editor Center link with the specific JavaScript
    ae_link = None
    try:
        # Find the specific AE link from the HTML we saw
        ae_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'ASSOCIATE_EDITOR_DASHBOARD')]")
        if ae_links:
            ae_link = ae_links[0]
        else:
            # Try JavaScript-based link
            js_links = driver.find_elements(By.XPATH, "//a[contains(@href, \"javascript:setField('XIK_POSTACT'\")]")
            for link in js_links:
                if "ASSOCIATE_EDITOR_DASHBOARD" in link.get_attribute("href"):
                    ae_link = link
                    break
    except Exception as e:
        print(f"Error finding AE link: {e}")
    
    if ae_link:
        print("Found Associate Editor Dashboard link, clicking...")
        ae_link.click()
        time.sleep(3)
    
    # Now we should be on the AE dashboard
    # Get ALL status queues, not just specific ones
    dashboard_html = driver.page_source
    soup = BeautifulSoup(dashboard_html, "html.parser")
    
    # Find all clickable numbers in the dashboard
    print("\nFinding ALL manuscript queues...")
    
    # Look for table cells with numbers that are clickable
    all_links = driver.find_elements(By.TAG_NAME, "a")
    manuscript_queue_links = []
    
    for link in all_links:
        try:
            text = link.text.strip()
            # Check if it's a number and greater than 0
            if text.isdigit() and int(text) > 0:
                # Get the parent td and next sibling to find status text
                parent = link.find_element(By.XPATH, "..")
                if parent.tag_name == "td":
                    # Try to find the status text
                    following_tds = parent.find_elements(By.XPATH, "following-sibling::td")
                    if following_tds:
                        status_text = following_tds[0].text.strip()
                        if status_text:  # Make sure there's a status
                            manuscript_queue_links.append({
                                'link': link,
                                'count': int(text),
                                'status': status_text
                            })
                            print(f"  Found queue: {status_text} ({text} manuscripts)")
        except:
            continue
    
    print(f"\nTotal queues found: {len(manuscript_queue_links)}")
    
    # Click through each queue and collect manuscripts
    for queue in manuscript_queue_links:
        try:
            print(f"\nProcessing queue: {queue['status']} ({queue['count']} manuscripts)")
            
            # Click the link
            queue['link'].click()
            time.sleep(3)
            
            # Parse manuscripts on this page
            ms_html = driver.page_source
            ms_soup = BeautifulSoup(ms_html, "html.parser")
            
            # Look for manuscript tables
            tables = ms_soup.find_all("table")
            for table in tables:
                # Check if this table contains MOR manuscript IDs
                if table.find(text=re.compile(r"MOR-\d{4}-\d+")):
                    print("  Found manuscript table")
                    
                    # Parse manuscript data
                    mdata = mor_journal.parse_manuscript_panel(str(table), flagged_emails=flagged_emails)
                    ms_id = mdata["Manuscript #"]
                    
                    if ms_id and ms_id not in manuscripts:
                        manuscripts[ms_id] = mdata
                        referee_count = len(mdata.get("Referees", []))
                        print(f"    Parsed manuscript {ms_id}: {referee_count} referees")
                        
                        # Print referee names
                        for ref in mdata.get("Referees", []):
                            print(f"      - {ref.get('Referee Name', 'Unknown')} ({ref.get('Status', 'Unknown')})")
            
            # Try to go back to the dashboard
            try:
                # Look for a back button or dashboard link
                back_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'Dashboard') or contains(text(), 'Back') or contains(text(), 'Return')]")
                if back_links:
                    back_links[0].click()
                else:
                    driver.back()
                time.sleep(2)
            except:
                driver.back()
                time.sleep(2)
                
        except Exception as e:
            print(f"  Error processing queue: {e}")
            # Try to recover by going back
            try:
                driver.back()
                time.sleep(2)
            except:
                pass
    
    return list(manuscripts.values())

def test_mor_comprehensive_fix():
    """Test MOR with the comprehensive fix."""
    print("\n" + "="*60)
    print("TESTING MOR JOURNAL FIX - EXPECTING 6 REFEREES")
    print("="*60)
    
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(options=options)
    
    try:
        # Create MOR journal instance
        mor = MORJournal(driver, debug=True)
        
        # Login
        print("Logging in to MOR...")
        mor.login()
        time.sleep(3)
        
        # Get flagged emails
        from core.email_utils import fetch_starred_emails
        flagged_emails = fetch_starred_emails("MOR")
        print(f"Retrieved {len(flagged_emails)} flagged emails")
        
        # Scrape all manuscripts
        manuscripts = scrape_all_mor_manuscripts(driver, mor, flagged_emails)
        
        # Count total referees
        total_referees = sum(len(m.get("Referees", [])) for m in manuscripts)
        
        print(f"\n=== MOR COMPREHENSIVE RESULTS ===")
        print(f"Total manuscripts found: {len(manuscripts)}")
        print(f"Total referees found: {total_referees}")
        print(f"Expected referees: 6")
        
        if total_referees < 6:
            print(f"\n⚠️  STILL MISSING {6 - total_referees} REFEREES")
            print("\nManuscripts found:")
            for m in manuscripts:
                print(f"  - {m.get('Manuscript #', 'Unknown')}: {len(m.get('Referees', []))} referees")
        else:
            print("\n✅ SUCCESS! Found all 6 referees!")
            
        # Also run the standard scraping to compare
        print("\n\nRunning standard MOR scraping for comparison...")
        standard_manuscripts = mor.scrape_manuscripts_and_emails()
        standard_referees = sum(len(m.get("Referees", [])) for m in standard_manuscripts)
        print(f"Standard scraping found: {len(standard_manuscripts)} manuscripts, {standard_referees} referees")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Save debug info
        with open('mor_error_debug.html', 'w') as f:
            f.write(driver.page_source)
    
    finally:
        driver.quit()

if __name__ == "__main__":
    test_mor_comprehensive_fix()