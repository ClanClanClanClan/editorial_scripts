#!/usr/bin/env python3
"""
MOR DETAILED EXTRACTION TEST - Shows every single detail extracted
"""

import sys
import os
import time
import json
from datetime import datetime

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.gmail_verification import fetch_latest_verification_code

print("="*80)
print("🔬 MOR ULTRA-DETAILED EXTRACTION TEST")
print("="*80)

extracted_data = {
    "extraction_timestamp": datetime.now().isoformat(),
    "manuscripts": []
}

driver = None
try:
    # 1. Setup Chrome
    print("\n📌 PHASE 1: BROWSER SETUP")
    print("-"*40)
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 10)
    print("   ✅ Chrome initialized")
    print("   Window size:", driver.get_window_size())

    # 2. Navigate to MOR
    print("\n📌 PHASE 2: NAVIGATION")
    print("-"*40)
    print("   Navigating to: https://mc.manuscriptcentral.com/mathor")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)
    print(f"   Current URL: {driver.current_url}")
    print(f"   Page title: {driver.title}")

    # Handle cookies
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
        reject.click()
        time.sleep(2)
        print("   ✅ Cookies rejected")
    except:
        print("   ℹ️ No cookie banner found")

    # 3. Login
    print("\n📌 PHASE 3: AUTHENTICATION")
    print("-"*40)
    print("   Entering credentials...")

    # Wait for login form
    wait.until(EC.presence_of_element_located((By.ID, "USERID")))

    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))
    print(f"   Email: {os.getenv('MOR_EMAIL')}")

    login_time = time.time()
    print(f"   Login timestamp: {login_time}")
    driver.find_element(By.ID, "logInButton").click()
    time.sleep(5)

    # Handle 2FA
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("\n   🔑 2FA DETECTED")
        print("   Fetching fresh verification code...")

        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_time
        )

        if code:
            print(f"   ✅ Got fresh code: {code}")
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            driver.find_element(By.ID, "VERIFY_BTN").click()
            time.sleep(10)
            print("   Submitted 2FA code")
        else:
            print("   ❌ No fresh code received")
            raise Exception("2FA failed - no code")
    except Exception as e:
        if "TOKEN_VALUE" not in str(e):
            print(f"   ℹ️ No 2FA required or different error: {e}")

    # Verify login
    print("\n   Verifying login status...")
    print(f"   Current URL: {driver.current_url}")
    print(f"   Page title: {driver.title}")

    # 4. Navigate to AE Center
    print("\n📌 PHASE 4: ASSOCIATE EDITOR CENTER")
    print("-"*40)

    ae_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Editor")))
    ae_link.click()
    time.sleep(3)
    print("   ✅ Navigated to AE Center")
    print(f"   Current URL: {driver.current_url}")

    # 5. Find manuscript categories
    print("\n📌 PHASE 5: MANUSCRIPT CATEGORIES")
    print("-"*40)

    links = driver.find_elements(By.TAG_NAME, "a")
    categories = []
    for link in links:
        text = link.text.strip()
        if text and any(word in text for word in ['Awaiting', 'Review', 'Decision', 'Assignment']):
            if 'Details Reports' not in text:  # Skip report links
                categories.append(text)

    unique_categories = list(set(categories))
    print(f"   Found {len(unique_categories)} categories:")
    for i, cat in enumerate(unique_categories, 1):
        print(f"      {i}. {cat}")

    # 6. Extract manuscripts from each category
    print("\n📌 PHASE 6: MANUSCRIPT EXTRACTION")
    print("-"*40)

    for category in unique_categories[:2]:  # Process first 2 categories
        print(f"\n   📂 CATEGORY: {category}")
        print("   " + "-"*30)

        try:
            # Navigate to category
            cat_link = driver.find_element(By.LINK_TEXT, category)
            cat_link.click()
            time.sleep(3)

            # Find manuscript rows
            ms_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
            print(f"   Found {len(ms_rows)} manuscripts")

            if ms_rows:
                # Extract first manuscript in detail
                row = ms_rows[0]
                ms_data = {
                    "category": category,
                    "extraction_time": datetime.now().isoformat()
                }

                # Get manuscript ID
                try:
                    ms_link = row.find_element(By.XPATH, ".//a[contains(text(), 'MOR-')]")
                    ms_id = ms_link.text
                    ms_data["manuscript_id"] = ms_id
                    print(f"\n   📄 MANUSCRIPT: {ms_id}")
                    print("   " + "-"*25)
                except:
                    print("   ⚠️ Could not extract manuscript ID")

                # Extract row data
                cells = row.find_elements(By.TAG_NAME, "td")
                print(f"   Row has {len(cells)} columns")

                for i, cell in enumerate(cells):
                    cell_text = cell.text.strip()
                    if cell_text:
                        print(f"   Column {i}: {cell_text[:50]}...")
                        ms_data[f"column_{i}"] = cell_text

                # Open manuscript details
                print("\n   Opening manuscript details...")
                try:
                    # Try clicking checkmark/view icon
                    view_icon = row.find_element(By.XPATH, ".//img[contains(@src, 'check') or contains(@src, 'view')]")
                    parent = view_icon.find_element(By.XPATH, "./parent::*")
                    parent.click()
                except:
                    # Fallback to clicking manuscript ID
                    ms_link.click()

                time.sleep(5)

                # Check if popup opened
                handles = driver.window_handles
                if len(handles) > 1:
                    print("   ✅ Popup window opened")
                    driver.switch_to.window(handles[-1])

                    # Extract detailed data
                    print("\n   📊 EXTRACTING DETAILED DATA:")
                    print("   " + "-"*25)

                    # Title
                    try:
                        title_elem = driver.find_element(By.XPATH, "//b[contains(text(), 'Title')]/following::td[1]")
                        title = title_elem.text
                        ms_data["title"] = title
                        print(f"   Title: {title[:80]}...")
                    except:
                        try:
                            # Alternative method
                            page_text = driver.page_source
                            if "Manuscript Title:" in page_text:
                                start = page_text.index("Manuscript Title:") + 17
                                end = page_text.index("<", start)
                                title = page_text[start:end].strip()
                                ms_data["title"] = title
                                print(f"   Title (alt): {title[:80]}...")
                        except:
                            print("   ⚠️ Could not extract title")

                    # Authors
                    try:
                        author_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'Author') and contains(., '@')]")
                        authors = []
                        for row in author_rows:
                            text = row.text
                            if '@' in text:
                                authors.append(text)
                                print(f"   Author: {text[:60]}...")
                        ms_data["authors"] = authors
                        ms_data["author_count"] = len(authors)
                    except:
                        print("   ⚠️ Could not extract authors")

                    # Decision/Status
                    try:
                        decision_elem = driver.find_element(By.XPATH, "//*[contains(text(), 'Decision:')]/following::*[1]")
                        decision = decision_elem.text
                        ms_data["decision"] = decision
                        print(f"   Decision: {decision}")
                    except:
                        print("   ⚠️ No decision found")

                    # Dates
                    try:
                        date_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Date')]")
                        dates = {}
                        for elem in date_elements:
                            text = elem.text
                            if ':' in text:
                                key = text.split(':')[0].strip()
                                try:
                                    value = elem.find_element(By.XPATH, "./following::*[1]").text
                                    dates[key] = value
                                    print(f"   {key}: {value}")
                                except:
                                    pass
                        ms_data["dates"] = dates
                    except:
                        print("   ⚠️ No dates found")

                    # Look for Review History
                    print("\n   🔍 CHECKING FOR REFEREE DATA:")
                    print("   " + "-"*25)

                    try:
                        # Try to find review link
                        review_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Review")
                        review_link.click()
                        time.sleep(3)
                        print("   ✅ Opened review section")

                        # Look for referee information
                        referee_rows = driver.find_elements(By.XPATH, "//tr[contains(., '@') and (contains(., 'Invited') or contains(., 'Agreed') or contains(., 'Complete') or contains(., 'Declined'))]")

                        referees = []
                        print(f"   Found {len(referee_rows)} potential referees")

                        for i, row in enumerate(referee_rows[:5], 1):  # First 5 referees
                            ref_data = {}
                            row_text = row.text

                            # Extract email
                            import re
                            email_match = re.search(r'[\w.+-]+@[\w.-]+\.\w+', row_text)
                            if email_match:
                                ref_data["email"] = email_match.group()
                                print(f"   Referee {i} email: {ref_data['email']}")

                            # Extract status
                            for status in ['Invited', 'Agreed', 'Declined', 'Complete', 'Pending']:
                                if status in row_text:
                                    ref_data["status"] = status
                                    print(f"   Referee {i} status: {status}")
                                    break

                            # Extract name if available
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if cells:
                                name_cell = cells[0].text.strip()
                                if name_cell and '@' not in name_cell:
                                    ref_data["name"] = name_cell
                                    print(f"   Referee {i} name: {name_cell}")

                            if ref_data:
                                referees.append(ref_data)

                        ms_data["referees"] = referees
                        ms_data["referee_count"] = len(referees)

                    except Exception as e:
                        print(f"   ⚠️ Could not extract referee data: {str(e)[:50]}")

                    # Get page source for debugging
                    page_source = driver.page_source
                    ms_data["page_length"] = len(page_source)
                    print(f"\n   Page source length: {len(page_source)} characters")

                    # Close popup
                    driver.close()
                    driver.switch_to.window(handles[0])
                    print("   ✅ Closed popup, returned to main window")

                else:
                    print("   ⚠️ No popup - data may be inline")
                    # Try to extract inline data
                    page_text = driver.page_source[:2000]
                    ms_data["inline_preview"] = page_text

                # Add to results
                extracted_data["manuscripts"].append(ms_data)

            # Navigate back to AE Center for next category
            driver.get("https://mc.manuscriptcentral.com/mathor")
            time.sleep(2)
            ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Editor")
            ae_link.click()
            time.sleep(2)

        except Exception as e:
            print(f"   ❌ Error processing category {category}: {str(e)[:100]}")

    # 7. Summary
    print("\n" + "="*80)
    print("📊 EXTRACTION SUMMARY")
    print("="*80)

    print(f"\nTotal manuscripts extracted: {len(extracted_data['manuscripts'])}")

    for i, ms in enumerate(extracted_data['manuscripts'], 1):
        print(f"\n📄 Manuscript {i}:")
        print(f"   ID: {ms.get('manuscript_id', 'Unknown')}")
        print(f"   Category: {ms.get('category', 'Unknown')}")
        print(f"   Title: {ms.get('title', 'Not extracted')[:60]}...")
        print(f"   Authors: {ms.get('author_count', 0)} found")
        print(f"   Referees: {ms.get('referee_count', 0)} found")

        if 'referees' in ms:
            print("   Referee details:")
            for j, ref in enumerate(ms['referees'][:3], 1):
                print(f"      {j}. {ref.get('email', 'No email')} - {ref.get('status', 'Unknown status')}")

    # Save results
    output_file = f"/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/dev/mf/outputs/mor_detailed_extraction_{int(time.time())}.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(extracted_data, f, indent=2)

    print(f"\n💾 Results saved to: {output_file}")

except Exception as e:
    print(f"\n❌ FATAL ERROR: {e}")
    import traceback
    traceback.print_exc()

finally:
    if driver:
        print("\n🧹 Cleanup: Closing browser in 10 seconds...")
        time.sleep(10)
        driver.quit()
        print("✅ Browser closed")

print("\n" + "="*80)
print("🎯 DETAILED EXTRACTION TEST COMPLETE")
print("="*80)