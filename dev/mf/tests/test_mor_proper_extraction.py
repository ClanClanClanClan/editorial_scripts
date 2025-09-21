#!/usr/bin/env python3
"""
MOR PROPER EXTRACTION - DO NOT NAVIGATE BACK!
"""

import sys
import os
import time
import re
import json

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from core.gmail_verification import fetch_latest_verification_code

print("="*80)
print("🎯 MOR PROPER EXTRACTION - EXTRACT WITHOUT NAVIGATING BACK")
print("="*80)

RESULTS = {
    "manuscripts": [],
    "extraction_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "total_manuscripts": 0
}

driver = None
try:
    # Setup
    print("\n1. Browser Setup")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    wait = WebDriverWait(driver, 15)
    print("   ✅ Chrome ready")

    # Navigate
    print("\n2. Navigate to MOR")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(5)

    # Handle cookies
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
        reject.click()
        time.sleep(2)
        print("   ✅ Cookies rejected")
    except:
        pass

    # Login
    print("\n3. Login")
    wait.until(EC.presence_of_element_located((By.ID, "USERID")))
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    login_time = time.time()
    driver.find_element(By.ID, "logInButton").click()
    print("   ✅ Credentials submitted")

    # Handle 2FA
    print("\n4. 2FA Handling")
    time.sleep(5)

    if "verification" in driver.page_source.lower() or "TOKEN_VALUE" in driver.page_source:
        print("   2FA detected")
        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_time
        )

        if code:
            print(f"   Got code: {code}")
            # Enter code via JavaScript
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            time.sleep(1)

            # Multiple methods to click the VERIFY_BTN
            print("   Trying to click VERIFY_BTN...")
            
            # Method 1: JavaScript click by ID
            try:
                driver.execute_script("document.getElementById('VERIFY_BTN').click();")
                print("   ✅ Clicked via JavaScript (ID)")
            except:
                # Method 2: Find and click with Selenium
                try:
                    verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
                    driver.execute_script("arguments[0].click();", verify_btn)
                    print("   ✅ Clicked via JavaScript (element)")
                except:
                    # Method 3: Send Enter key to the token field
                    token_field = driver.find_element(By.ID, "TOKEN_VALUE")
                    token_field.send_keys(Keys.RETURN)
                    print("   ✅ Sent Enter key")

            time.sleep(10)

    # Check if logged in
    print("\n5. Login Status Check")
    if "Associate Editor" in driver.page_source or "editor center" in driver.page_source.lower():
        print("   ✅ Logged in successfully!")
    else:
        print("   ⚠️ May not be logged in, continuing anyway...")
        print(f"   Current URL: {driver.current_url}")
        print(f"   Page title: {driver.title}")

    # Navigate to AE Center - try multiple methods
    print("\n6. Navigate to Associate Editor Center")
    ae_found = False
    
    # Method 1: Exact text
    try:
        ae_link = driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        ae_link.click()
        ae_found = True
        print("   ✅ Found via exact text")
    except:
        pass
    
    # Method 2: Partial text
    if not ae_found:
        try:
            ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Associate Editor")
            ae_link.click()
            ae_found = True
            print("   ✅ Found via partial text")
        except:
            pass
    
    # Method 3: Search all links
    if not ae_found:
        links = driver.find_elements(By.TAG_NAME, "a")
        for link in links:
            text = link.text.lower()
            if "associate" in text and "editor" in text:
                link.click()
                ae_found = True
                print(f"   ✅ Found link: {link.text}")
                break
    
    if not ae_found:
        print("   ❌ Could not find AE Center link")
        print("   Available links:")
        for link in driver.find_elements(By.TAG_NAME, "a")[:20]:
            if link.text:
                print(f"      - {link.text}")
    else:
        time.sleep(5)
        print("   ✅ In AE Center")

    # Find categories
    print("\n7. Find Categories")
    categories = []
    for link in driver.find_elements(By.TAG_NAME, "a"):
        text = link.text.strip()
        if text and any(kw in text for kw in ['Review', 'Awaiting', 'Decision']):
            categories.append({
                "text": text,
                "element": link
            })
            print(f"   Found: {text}")

    # Process first category with manuscripts
    if categories:
        cat = categories[0]
        print(f"\n8. Processing category: {cat['text']}")
        cat["element"].click()
        time.sleep(5)

        # Find manuscripts
        manuscript_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
        print(f"   Found {len(manuscript_rows)} manuscripts")

        # Process first manuscript
        if manuscript_rows:
            row = manuscript_rows[0]

            # Extract ID
            row_text = row.text
            mor_match = re.search(r'MOR-\d{4}-\d+', row_text)
            if mor_match:
                manuscript_id = mor_match.group()
                print(f"\n   Processing: {manuscript_id}")

                # Find Take Action button
                action_button = row.find_element(By.XPATH, ".//input[@value='Take Action']")
                
                # Store main window
                main_window = driver.current_window_handle
                
                # Click Take Action
                action_button.click()
                time.sleep(5)
                
                print("\n   📊 EXTRACTING DATA FROM MANUSCRIPT:")
                print("   " + "-"*40)
                
                # Check if opened in new window
                if len(driver.window_handles) > 1:
                    print("   ✅ Opened in new window")
                    for window in driver.window_handles:
                        if window != main_window:
                            driver.switch_to.window(window)
                            break
                
                # NOW EXTRACT THE DATA - DO NOT NAVIGATE BACK!
                manuscript_data = {
                    "manuscript_id": manuscript_id,
                    "category": cat["text"],
                    "extracted_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Get page text
                page_text = driver.find_element(By.TAG_NAME, "body").text
                
                # Extract title
                title_match = re.search(r'Title[:\s]+(.+?)[\n\r]', page_text, re.IGNORECASE)
                if title_match:
                    manuscript_data["title"] = title_match.group(1).strip()
                    print(f"   Title: {manuscript_data['title'][:100]}")
                
                # Look for tabs (Referees, Authors, etc)
                print("\n   Looking for tabs...")
                tabs = driver.find_elements(By.XPATH, "//a[contains(@class, 'tab') or contains(@onclick, 'tab')]")
                print(f"   Found {len(tabs)} potential tabs")
                for tab in tabs[:10]:
                    print(f"      - {tab.text or 'No text'}")
                
                # Try to find referee tab
                print("\n   📋 REFEREES:")
                referee_tabs = driver.find_elements(By.XPATH,
                    "//a[contains(text(), 'Referee') or contains(text(), 'Reviewer')]")
                
                if referee_tabs:
                    print(f"   Found {len(referee_tabs)} referee tabs")
                    referee_tabs[0].click()
                    time.sleep(3)
                    
                    # Extract referee data
                    referee_rows = driver.find_elements(By.XPATH,
                        "//tr[contains(., 'Invited') or contains(., 'Agreed') or contains(., 'Declined')]")
                    
                    manuscript_data["referees"] = []
                    print(f"   Found {len(referee_rows)} referee rows")
                    
                    for i, ref_row in enumerate(referee_rows[:5], 1):
                        ref_text = ref_row.text
                        ref_data = {"row": i, "text": ref_text[:200]}
                        
                        # Extract name
                        cells = ref_row.find_elements(By.TAG_NAME, "td")
                        if len(cells) > 1:
                            ref_data["name"] = cells[1].text.strip()
                        
                        # Extract status
                        for status in ['Invited', 'Agreed', 'Declined', 'Complete']:
                            if status in ref_text:
                                ref_data["status"] = status
                                break
                        
                        manuscript_data["referees"].append(ref_data)
                        print(f"      Referee {i}: {ref_data.get('name', 'Unknown')} - {ref_data.get('status', 'Unknown')}")
                else:
                    print("   No referee tabs found")
                
                # Try to find author tab
                print("\n   👥 AUTHORS:")
                author_tabs = driver.find_elements(By.XPATH,
                    "//a[contains(text(), 'Author') or contains(text(), 'Manuscript Info')]")
                
                if author_tabs:
                    print(f"   Found {len(author_tabs)} author tabs")
                    author_tabs[0].click()
                    time.sleep(3)
                    
                    # Extract author data
                    author_rows = driver.find_elements(By.XPATH,
                        "//tr[contains(., '@') and not(contains(., 'Referee'))]")
                    
                    manuscript_data["authors"] = []
                    print(f"   Found {len(author_rows)} potential author rows")
                    
                    for i, auth_row in enumerate(author_rows[:5], 1):
                        auth_text = auth_row.text
                        auth_data = {"row": i, "text": auth_text[:200]}
                        
                        # Extract email
                        emails = re.findall(r'[\w.+-]+@[\w.-]+\.[a-z]+', auth_text, re.IGNORECASE)
                        if emails:
                            auth_data["email"] = emails[0]
                        
                        manuscript_data["authors"].append(auth_data)
                        print(f"      Author {i}: {auth_data.get('email', 'No email')}")
                else:
                    print("   No author tabs found")
                
                # Extract any visible metadata
                print("\n   📄 METADATA:")
                
                # Status
                status_match = re.search(r'Status[:\s]+(.+?)[\n\r]', page_text, re.IGNORECASE)
                if status_match:
                    manuscript_data["status"] = status_match.group(1).strip()
                    print(f"   Status: {manuscript_data['status']}")
                
                # Dates
                dates = re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}', page_text)
                if dates:
                    manuscript_data["dates"] = dates[:5]
                    print(f"   Dates found: {', '.join(dates[:3])}")
                
                # Keywords
                keywords_match = re.search(r'Keywords?[:\s]+(.+?)[\n\r]', page_text, re.IGNORECASE)
                if keywords_match:
                    manuscript_data["keywords"] = keywords_match.group(1).strip()
                    print(f"   Keywords: {manuscript_data['keywords'][:100]}")
                
                # Abstract
                abstract_match = re.search(r'Abstract[:\s]+(.+?)(?=\n[A-Z]|\Z)', page_text, re.IGNORECASE | re.DOTALL)
                if abstract_match:
                    manuscript_data["abstract"] = abstract_match.group(1).strip()[:500]
                    print(f"   Abstract: {len(manuscript_data.get('abstract', ''))} chars")
                
                # Store the extracted data
                RESULTS["manuscripts"].append(manuscript_data)
                RESULTS["total_manuscripts"] += 1
                
                print("\n   ✅ Manuscript data extracted!")
                
                # DO NOT NAVIGATE BACK - Close window if in popup
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(main_window)
                    print("   ✅ Closed manuscript window, back to main")

    # Summary
    print("\n" + "="*80)
    print("📊 EXTRACTION COMPLETE")
    print("="*80)
    
    print(f"\n✅ Total manuscripts extracted: {RESULTS['total_manuscripts']}")
    
    for ms in RESULTS["manuscripts"]:
        print(f"\n📄 {ms['manuscript_id']} ({ms['category']})")
        print(f"   Title: {ms.get('title', 'N/A')[:100]}")
        print(f"   Authors: {len(ms.get('authors', []))}")
        print(f"   Referees: {len(ms.get('referees', []))}")
        print(f"   Status: {ms.get('status', 'N/A')}")
        
        if ms.get("referees"):
            print("\n   REFEREE DETAILS:")
            for ref in ms["referees"][:3]:
                print(f"      - {ref.get('name', 'Unknown')}: {ref.get('status', '')}")
        
        if ms.get("authors"):
            print("\n   AUTHOR DETAILS:")
            for auth in ms["authors"][:3]:
                print(f"      - {auth.get('email', 'no email')}")

    # Save results
    output_file = f"/tmp/mor_proper_extraction_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

finally:
    if driver:
        print("\nKeeping browser open for 30 seconds...")
        print("CHECK THE BROWSER!")
        time.sleep(30)
        driver.quit()

print("\n" + "="*80)
print("EXTRACTION COMPLETE")
print("="*80)