#!/usr/bin/env python3
"""
MOR ALL CATEGORIES - FIND AND EXTRACT FROM EVERY CATEGORY
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
print("🎯 MOR ALL CATEGORIES EXTRACTION")
print("="*80)

RESULTS = {
    "manuscripts": [],
    "extraction_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "login_successful": False,
    "all_categories": [],
    "categories_with_manuscripts": [],
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
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")

            # Try multiple click methods
            try:
                driver.execute_script("""
                    var buttons = document.querySelectorAll('button');
                    for (var i = 0; i < buttons.length; i++) {
                        if (buttons[i].textContent.includes('Verify')) {
                            buttons[i].click();
                            return true;
                        }
                    }
                """)
            except:
                try:
                    token_field = driver.find_element(By.ID, "TOKEN_VALUE")
                    token_field.send_keys(Keys.RETURN)
                except:
                    pass

            time.sleep(10)

    # Check login
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        if token_field.is_displayed():
            print("   ⚠️ 2FA still visible")
    except:
        print("   ✅ Login successful")
        RESULTS["login_successful"] = True

    # Navigate to AE Center
    print("\n5. Navigate to Associate Editor Center")

    # Find AE link
    all_links = driver.find_elements(By.TAG_NAME, "a")
    ae_link = None

    for link in all_links:
        text = link.text.strip()
        if text and "associate editor" in text.lower():
            ae_link = link
            print(f"   Found: {text}")
            break

    if ae_link:
        ae_link.click()
        time.sleep(5)
        print("   ✅ In AE Center")

        # Find ALL categories
        print("\n6. Find ALL Categories")
        print("-"*40)

        all_links = driver.find_elements(By.TAG_NAME, "a")
        categories = []

        for link in all_links:
            text = link.text.strip()
            href = link.get_attribute("href")

            # Look for any link that might be a category
            if text and href and "queue" in href.lower():
                categories.append({
                    "text": text,
                    "href": href
                })
                RESULTS["all_categories"].append(text)
                print(f"   Found category: {text}")

        # Also check for specific keywords
        keywords = ['Review', 'Awaiting', 'Decision', 'Assignment', 'Submitted',
                   'Referee', 'Reports', 'Revision', 'Accept', 'Reject', 'Queue']

        for link in all_links:
            text = link.text.strip()
            href = link.get_attribute("href")

            if text and any(kw in text for kw in keywords):
                # Avoid duplicates
                if not any(c["text"] == text for c in categories):
                    categories.append({
                        "text": text,
                        "href": href
                    })
                    RESULTS["all_categories"].append(text)
                    print(f"   Found category: {text}")

        # Extract from each category
        print(f"\n7. Extract from {len(categories)} categories")
        print("-"*40)

        for cat in categories:
            print(f"\n📁 Category: {cat['text']}")

            try:
                if cat["href"]:
                    driver.get(cat["href"])
                else:
                    # Try clicking the link
                    link = driver.find_element(By.LINK_TEXT, cat["text"])
                    link.click()

                time.sleep(5)

                # Find manuscripts
                page_source = driver.page_source
                mor_matches = re.findall(r'MOR-\d{4}-\d{4}', page_source)

                if mor_matches:
                    unique_ids = list(set(mor_matches))
                    print(f"   ✅ Found {len(unique_ids)} manuscripts!")
                    RESULTS["categories_with_manuscripts"].append(cat["text"])

                    # Find manuscript rows
                    rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")

                    for row in rows:
                        ms_data = {
                            "category": cat["text"]
                        }

                        # Extract manuscript ID
                        mor_match = re.search(r'MOR-\d{4}-\d{4}', row.text)
                        if mor_match:
                            ms_data["manuscript_id"] = mor_match.group()
                            print(f"      📄 {ms_data['manuscript_id']}")

                            # Extract row details
                            cells = row.find_elements(By.TAG_NAME, "td")
                            cell_texts = []

                            for i, cell in enumerate(cells[:8]):
                                text = cell.text.strip()
                                if text:
                                    cell_texts.append(text[:100])

                                    # Extract specific info
                                    if i == 2:  # Title column
                                        ms_data["title"] = text[:200]
                                        print(f"         Title: {text[:60]}...")
                                    elif "@" in text:
                                        ms_data["author_info"] = text
                                    elif "days" in text.lower():
                                        ms_data["days"] = text

                            ms_data["cells"] = cell_texts

                            # Try to open popup
                            try:
                                ms_link = row.find_element(By.PARTIAL_LINK_TEXT, "MOR-")
                                ms_link.click()
                                time.sleep(3)

                                if len(driver.window_handles) > 1:
                                    original = driver.current_window_handle
                                    driver.switch_to.window(driver.window_handles[-1])

                                    popup_text = driver.find_element(By.TAG_NAME, "body").text

                                    # Extract emails
                                    emails = re.findall(r'[\w.+-]+@[\w.-]+\.[a-z]+', popup_text, re.IGNORECASE)
                                    if emails:
                                        ms_data["referee_emails"] = list(set(emails))
                                        print(f"         Emails: {len(ms_data['referee_emails'])}")

                                    # Count referee statuses
                                    for status in ['Invited', 'Agreed', 'Declined', 'Complete']:
                                        count = popup_text.count(status)
                                        if count > 0:
                                            ms_data[f"referee_{status.lower()}"] = count

                                    driver.close()
                                    driver.switch_to.window(original)
                            except:
                                pass

                            RESULTS["manuscripts"].append(ms_data)
                            RESULTS["total_manuscripts"] += 1
                else:
                    print(f"   No manuscripts in this category")

                # Return to AE Center
                driver.get("https://mc.manuscriptcentral.com/mathor")
                time.sleep(3)

                # Re-navigate to AE center
                try:
                    ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Associate Editor")
                    ae_link.click()
                    time.sleep(3)
                except:
                    pass

            except Exception as e:
                print(f"   Error: {str(e)[:100]}")

    # Summary
    print("\n" + "="*80)
    print("📊 EXTRACTION COMPLETE - ALL CATEGORIES SEARCHED")
    print("="*80)

    print(f"\n✅ Login successful: {RESULTS['login_successful']}")
    print(f"✅ Total categories found: {len(RESULTS['all_categories'])}")
    print("\nAll categories:")
    for cat in RESULTS["all_categories"]:
        print(f"   - {cat}")

    print(f"\n✅ Categories with manuscripts: {len(RESULTS['categories_with_manuscripts'])}")
    for cat in RESULTS["categories_with_manuscripts"]:
        print(f"   - {cat}")

    print(f"\n✅ Total manuscripts extracted: {RESULTS['total_manuscripts']}")

    for ms in RESULTS["manuscripts"]:
        print(f"\n📄 {ms.get('manuscript_id', 'Unknown')}")
        print(f"   Category: {ms.get('category')}")
        if "title" in ms:
            print(f"   Title: {ms['title'][:100]}...")
        if "author_info" in ms:
            print(f"   Author: {ms['author_info'][:60]}...")
        if "referee_emails" in ms:
            print(f"   Referee emails: {len(ms['referee_emails'])}")
            for email in ms["referee_emails"][:3]:
                print(f"      - {email}")

    # Save results
    output_file = f"/tmp/mor_all_categories_{int(time.time())}.json"
    with open(output_file, 'w') as f:
        json.dump(RESULTS, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")

    # Screenshot
    driver.save_screenshot("/tmp/mor_all_categories.png")
    print(f"📸 Screenshot: /tmp/mor_all_categories.png")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    if driver:
        driver.save_screenshot("/tmp/mor_all_categories_error.png")

finally:
    if driver:
        print("\nClosing in 20 seconds...")
        time.sleep(20)
        driver.quit()

print("\n" + "="*80)
print("ALL CATEGORIES EXTRACTION COMPLETE")
print("="*80)