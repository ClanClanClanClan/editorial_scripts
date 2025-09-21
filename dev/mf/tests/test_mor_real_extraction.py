#!/usr/bin/env python3
"""
MOR REAL EXTRACTION - GET THE ACTUAL DATA
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
print("🎯 MOR REAL EXTRACTION - GET THE ACTUAL DATA")
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
        print("   ⏳ Waiting for NEW 2FA email...")
        time.sleep(10)  # Wait for new email to arrive

        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_time
        )

        if code:
            print(f"   Got code: {code}")
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")

            # Click the VERIFY_BTN
            try:
                verify_btn = driver.find_element(By.ID, "VERIFY_BTN")
                driver.execute_script("arguments[0].click();", verify_btn)
                print("   ✅ Clicked VERIFY_BTN")
            except:
                # Fallback
                token_field = driver.find_element(By.ID, "TOKEN_VALUE")
                token_field.send_keys(Keys.RETURN)

            time.sleep(10)

    # Navigate to AE Center - with better handling
    print("\n5. Navigate to Associate Editor Center")

    # CRITICAL: Refresh page after 2FA - this makes AE Center link clickable
    print("   🔄 Refreshing page after 2FA...")
    driver.refresh()
    time.sleep(5)

    # Try multiple methods to find AE Center
    ae_found = False

    # Method 1: Look for any link with "Editor" text
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        text = link.text.strip()
        if text and ("associate" in text.lower() or "editor" in text.lower()):
            print(f"   Found potential link: {text}")
            if "associate editor" in text.lower() or "editor center" in text.lower():
                link.click()
                ae_found = True
                print(f"   ✅ Clicked: {text}")
                break

    if not ae_found:
        print("   ⚠️ No AE Center link found, checking if already in AE Center...")
        # Check if we're already in AE Center by looking for categories
        if any(kw in driver.page_source for kw in ["Awaiting", "Review", "Decision"]):
            print("   ✅ Already in AE Center!")
            ae_found = True

    if ae_found:
        time.sleep(5)
        print("   ✅ In AE Center")
    else:
        print("   ❌ Could not navigate to AE Center")
        print(f"   Current URL: {driver.current_url}")
        print(f"   Page title: {driver.title}")

    # Find categories
    print("\n6. Find Categories")
    categories = []
    for link in driver.find_elements(By.TAG_NAME, "a"):
        text = link.text.strip()
        if text and any(kw in text for kw in ['Review', 'Awaiting', 'Decision']):
            categories.append({
                "text": text,
                "element": link
            })
            print(f"   Found: {text}")

    # Process the category with manuscripts (Awaiting Reviewer Reports)
    if categories:
        # Find the category with manuscripts
        cat = None
        for c in categories:
            if "Awaiting Reviewer" in c["text"]:
                cat = c
                break
        if not cat:
            cat = categories[0]
        print(f"\n7. Processing category: {cat['text']}")
        print("-"*60)

        cat["element"].click()
        time.sleep(5)

        # Find manuscripts
        manuscript_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
        print(f"   Found {len(manuscript_rows)} manuscripts")

        # Process first manuscript
        if manuscript_rows:
            row = manuscript_rows[0]

            # Extract ID from row
            row_text = row.text
            mor_match = re.search(r'MOR-\d{4}-\d+', row_text)
            if mor_match:
                manuscript_id = mor_match.group()
                print(f"\n   Processing: {manuscript_id}")

                # Find clickable element
                check_icon = row.find_element(By.XPATH, ".//img[contains(@src, 'check')]/parent::*")

                # Store main window
                main_window = driver.current_window_handle

                # Click manuscript
                check_icon.click()
                time.sleep(5)

                # Check if opened in new window
                if len(driver.window_handles) > 1:
                    print("   ✅ Opened in new window")
                    for window in driver.window_handles:
                        if window != main_window:
                            driver.switch_to.window(window)
                            break

                # Extract manuscript data
                print("\n   📊 EXTRACTING DATA:")
                print("   " + "-"*40)

                manuscript_data = {
                    "manuscript_id": manuscript_id,
                    "category": cat["text"]
                }

                # Find and extract referees
                print("\n   📋 REFEREES:")
                referee_tabs = driver.find_elements(By.XPATH,
                    "//a[contains(text(), 'Referee') or contains(text(), 'Reviewer')]")

                if referee_tabs:
                    referee_tabs[0].click()
                    time.sleep(3)

                # Find referee rows
                referee_rows = driver.find_elements(By.XPATH,
                    "//tr[contains(., 'Invited') or contains(., 'Agreed') or contains(., 'Declined')]")

                manuscript_data["referees"] = []
                print(f"      Found {len(referee_rows)} referee rows")

                for i, ref_row in enumerate(referee_rows[:5], 1):
                    ref_text = ref_row.text
                    ref_data = {
                        "row": i,
                        "text": ref_text[:200]
                    }

                    # Extract name
                    cells = ref_row.find_elements(By.TAG_NAME, "td")
                    if len(cells) > 1:
                        ref_data["name"] = cells[1].text.strip()

                    # Extract status
                    for status in ['Invited', 'Agreed', 'Declined', 'Complete']:
                        if status in ref_text:
                            ref_data["status"] = status
                            break

                    # Try to extract email via popup
                    try:
                        popup_links = ref_row.find_elements(By.XPATH,
                            ".//a[contains(@href,'mailpopup') or contains(@onclick,'mailpopup')]")

                        if popup_links:
                            original = driver.current_window_handle
                            popup_links[0].click()
                            time.sleep(2)

                            if len(driver.window_handles) > len([main_window, driver.current_window_handle]):
                                for window in driver.window_handles:
                                    if window not in [main_window, driver.current_window_handle, original]:
                                        driver.switch_to.window(window)
                                        break

                                # Extract email from popup
                                popup_text = driver.find_element(By.TAG_NAME, "body").text
                                emails = re.findall(r'[\w.+-]+@[\w.-]+\.[a-z]+', popup_text, re.IGNORECASE)
                                if emails:
                                    ref_data["email"] = emails[0]

                                driver.close()
                                driver.switch_to.window(original)
                    except:
                        pass

                    manuscript_data["referees"].append(ref_data)
                    print(f"      Referee {i}: {ref_data.get('name', 'Unknown')} - {ref_data.get('status', 'Unknown')} - {ref_data.get('email', 'No email')}")

                # Find and extract authors
                print("\n   👥 AUTHORS:")
                author_tabs = driver.find_elements(By.XPATH,
                    "//a[contains(text(), 'Author') or contains(text(), 'Manuscript Info')]")

                if author_tabs:
                    author_tabs[0].click()
                    time.sleep(3)

                # Look for author information
                author_sections = driver.find_elements(By.XPATH,
                    "//*[contains(text(), 'Corresponding Author') or contains(text(), 'Author Details')]")

                manuscript_data["authors"] = []

                # Find author rows/sections
                author_rows = driver.find_elements(By.XPATH,
                    "//tr[contains(., '@') and not(contains(., 'Referee'))]")[:5]

                for i, auth_row in enumerate(author_rows, 1):
                    auth_text = auth_row.text
                    auth_data = {
                        "row": i,
                        "text": auth_text[:200]
                    }

                    # Extract email
                    emails = re.findall(r'[\w.+-]+@[\w.-]+\.[a-z]+', auth_text, re.IGNORECASE)
                    if emails:
                        auth_data["email"] = emails[0]

                    # Extract name (before email typically)
                    if emails:
                        name_part = auth_text.split(emails[0])[0].strip()
                        # Clean up name
                        name_part = re.sub(r'\d+', '', name_part).strip()
                        if len(name_part) > 2:
                            auth_data["name"] = name_part

                    manuscript_data["authors"].append(auth_data)
                    print(f"      Author {i}: {auth_data.get('name', 'Unknown')} - {auth_data.get('email', 'No email')}")

                # Extract metadata
                print("\n   📄 METADATA:")
                page_text = driver.find_element(By.TAG_NAME, "body").text

                # Title
                title_match = re.search(r'Title[:\s]+(.+?)[\n\r]', page_text, re.IGNORECASE)
                if title_match:
                    manuscript_data["title"] = title_match.group(1).strip()
                    print(f"      Title: {manuscript_data['title'][:100]}...")

                # Abstract
                abstract_match = re.search(r'Abstract[:\s]+(.+?)(?=\n[A-Z]|\Z)', page_text, re.IGNORECASE | re.DOTALL)
                if abstract_match:
                    manuscript_data["abstract"] = abstract_match.group(1).strip()[:500]
                    print(f"      Abstract: {len(manuscript_data.get('abstract', ''))} chars")

                # Keywords
                keywords_match = re.search(r'Keywords?[:\s]+(.+?)[\n\r]', page_text, re.IGNORECASE)
                if keywords_match:
                    manuscript_data["keywords"] = keywords_match.group(1).strip()
                    print(f"      Keywords: {manuscript_data['keywords'][:100]}")

                # Status
                status_match = re.search(r'Status[:\s]+(.+?)[\n\r]', page_text, re.IGNORECASE)
                if status_match:
                    manuscript_data["status"] = status_match.group(1).strip()
                    print(f"      Status: {manuscript_data['status']}")

                # Dates
                dates = re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}', page_text)
                if dates:
                    manuscript_data["dates"] = dates[:5]
                    print(f"      Dates found: {dates[:3]}")

                RESULTS["manuscripts"].append(manuscript_data)
                RESULTS["total_manuscripts"] += 1

                # Close manuscript window
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(main_window)

    # Summary
    print("\n" + "="*80)
    print("📊 EXTRACTION COMPLETE - REAL DATA")
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
                print(f"      - {ref.get('name', 'Unknown')}: {ref.get('status', '')} ({ref.get('email', 'no email')})")

        if ms.get("authors"):
            print("\n   AUTHOR DETAILS:")
            for auth in ms["authors"][:3]:
                print(f"      - {auth.get('name', 'Unknown')}: {auth.get('email', 'no email')}")

    # Save results
    output_file = f"/tmp/mor_real_extraction_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

finally:
    if driver:
        print("\nClosing in 30 seconds...")
        time.sleep(30)
        driver.quit()

print("\n" + "="*80)
print("REAL EXTRACTION COMPLETE")
print("="*80)
