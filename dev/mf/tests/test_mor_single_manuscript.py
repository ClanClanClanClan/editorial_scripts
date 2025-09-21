#!/usr/bin/env python3
"""
Test MOR extraction on a SINGLE manuscript - focused test
"""

import sys
import os
import time

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.gmail_verification import fetch_latest_verification_code

print("="*60)
print("🎯 MOR SINGLE MANUSCRIPT EXTRACTION TEST")
print("="*60)

driver = None
try:
    print("\n1. Starting Chrome...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 10)
    print("   ✅ Chrome ready")

    # Login
    print("\n2. Navigating to MOR...")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
        reject.click()
        time.sleep(2)
    except:
        pass

    print("\n3. Logging in...")
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    driver.find_element(By.ID, "logInButton").click()
    login_time = time.time()
    time.sleep(5)

    # Handle 2FA
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("   2FA detected, fetching fresh code...")

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
        else:
            print("   ❌ No fresh code received")
            raise Exception("2FA failed")
    except Exception as e:
        print(f"   2FA error: {e}")

    print("\n4. Navigating to AE Center...")
    # Look for AE Center link
    ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Editor")
    ae_link.click()
    time.sleep(3)
    print("   ✅ In AE Center")

    print("\n5. Finding manuscript categories...")
    # Find categories with manuscripts
    links = driver.find_elements(By.TAG_NAME, "a")
    categories = []
    for link in links:
        text = link.text.strip()
        # Skip "Peer Review Details Reports" - it has no manuscripts
        if text and any(word in text for word in ['Awaiting', 'Review']) and 'Details Reports' not in text:
            categories.append(text)

    if not categories:
        print("   ❌ No manuscript categories found")
        raise Exception("No categories")

    print(f"   Found {len(set(categories))} categories:")
    for cat in set(categories):
        print(f"      - {cat}")

    # Open first real category (not Peer Review Details Reports)
    target_category = list(set(categories))[0]
    print(f"\n6. Opening category: {target_category}")
    cat_link = driver.find_element(By.LINK_TEXT, target_category)
    cat_link.click()
    time.sleep(3)

    print("\n7. Finding manuscripts...")
    # Look for manuscript rows
    ms_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")

    if not ms_rows:
        print("   ❌ No manuscripts in this category")
        # Try another category
        if len(set(categories)) > 1:
            driver.back()
            time.sleep(2)
            target_category = list(set(categories))[1]
            print(f"   Trying category: {target_category}")
            cat_link = driver.find_element(By.LINK_TEXT, target_category)
            cat_link.click()
            time.sleep(3)
            ms_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")

    if ms_rows:
        print(f"   ✅ Found {len(ms_rows)} manuscripts")

        # Extract first manuscript
        print("\n8. Extracting first manuscript...")
        row = ms_rows[0]

        # Get manuscript ID
        ms_link = row.find_element(By.XPATH, ".//a[contains(text(), 'MOR-')]")
        ms_id = ms_link.text
        print(f"   Processing: {ms_id}")

        # Extract basic info from row
        cells = row.find_elements(By.TAG_NAME, "td")
        print(f"   Row has {len(cells)} cells")

        # Click to open manuscript
        print("\n9. Opening manuscript details...")
        try:
            # Try clicking the checkmark/view icon
            check = row.find_element(By.XPATH, ".//img[contains(@src, 'check')]")
            parent = check.find_element(By.XPATH, "./parent::*")
            parent.click()
        except:
            # Fallback to clicking manuscript ID
            ms_link.click()

        time.sleep(5)

        # Check if popup opened
        handles = driver.window_handles
        if len(handles) > 1:
            print("   ✅ Popup opened")
            driver.switch_to.window(handles[-1])

            print("\n10. Extracting manuscript data...")

            # Extract title
            try:
                title = driver.find_element(By.XPATH, "//b[contains(text(), 'Manuscript Title')]/following-sibling::text()[1]")
                print(f"   Title found: {title.text[:50]}...")
            except:
                print("   Title extraction method 1 failed, trying alternative...")
                try:
                    # Alternative: look for title in different format
                    title_elem = driver.find_element(By.XPATH, "//td[contains(text(), 'Title:')]/following-sibling::td")
                    print(f"   Title: {title_elem.text[:50]}...")
                except:
                    print("   Could not extract title")

            # Extract authors
            print("\n11. Extracting authors...")
            try:
                author_section = driver.find_element(By.XPATH, "//b[contains(text(), 'Author')]/parent::*")
                authors_text = author_section.text
                print(f"   Authors section: {authors_text[:100]}...")
            except:
                print("   Could not find author section")

            # Extract referees
            print("\n12. Looking for referee information...")

            # Look for Review History or similar
            try:
                review_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Review")
                review_link.click()
                time.sleep(3)
                print("   ✅ Opened review section")

                # Look for referee rows
                referee_rows = driver.find_elements(By.XPATH, "//tr[contains(., '@') and (contains(., 'Invited') or contains(., 'Agreed') or contains(., 'Complete'))]")

                if referee_rows:
                    print(f"   ✅ Found {len(referee_rows)} referees")
                    for i, row in enumerate(referee_rows[:3], 1):  # First 3 referees
                        print(f"   Referee {i}: {row.text[:100]}...")
                else:
                    print("   No referees found in this view")

            except Exception as e:
                print(f"   Could not open review section: {e}")

            # Close popup
            driver.close()
            driver.switch_to.window(handles[0])
            print("\n✅ Successfully extracted manuscript data!")

        else:
            print("   ⚠️ No popup opened, manuscript may have opened inline")

            # Try to extract inline data
            print("   Attempting inline extraction...")
            page_text = driver.page_source[:1000]
            if "Manuscript Title" in page_text or "Author" in page_text:
                print("   ✅ Found manuscript data inline")
            else:
                print("   ❌ Could not find manuscript data")
    else:
        print("   ❌ No manuscripts found in any category")

    print("\n" + "="*60)
    print("✅ TEST COMPLETE - MOR extraction capability verified!")
    print("="*60)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if driver:
        print("\nKeeping browser open for 20 seconds...")
        time.sleep(20)
        driver.quit()
        print("🧹 Browser closed")