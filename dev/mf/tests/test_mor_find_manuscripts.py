#!/usr/bin/env python3
"""
FIND THE DAMN MANUSCRIPTS - Debug why we can't see them
"""

import sys
import os
import time
import re

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.gmail_verification import fetch_latest_verification_code

print("="*80)
print("🔍 FIND THE MANUSCRIPTS - PROPER NAVIGATION TEST")
print("="*80)

driver = None
try:
    # Setup
    print("\n1. Starting Chrome...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(10)
    wait = WebDriverWait(driver, 10)
    print("   ✅ Chrome ready")

    # Navigate
    print("\n2. Navigating to MOR...")
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        reject = driver.find_element(By.ID, "onetrust-reject-all-handler")
        reject.click()
        time.sleep(2)
        print("   ✅ Cookies rejected")
    except:
        pass

    # Login
    print("\n3. Logging in...")
    wait.until(EC.presence_of_element_located((By.ID, "USERID")))
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    login_time = time.time()
    driver.find_element(By.ID, "logInButton").click()
    time.sleep(5)

    # Handle 2FA
    try:
        token_field = driver.find_element(By.ID, "TOKEN_VALUE")
        print("   2FA detected, fetching code...")

        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_time
        )

        if code:
            print(f"   Got code: {code}")
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            driver.find_element(By.ID, "VERIFY_BTN").click()
            time.sleep(10)
        else:
            print("   ❌ No code received")
            raise Exception("2FA failed")
    except Exception as e:
        if "TOKEN_VALUE" not in str(e):
            print(f"   No 2FA or error: {e}")

    print("\n4. POST-LOGIN ANALYSIS")
    print("-"*40)
    print(f"   URL: {driver.current_url}")
    print(f"   Title: {driver.title}")

    # Check what's on the page
    page_text = driver.page_source[:5000]

    # Look for all links
    print("\n5. ALL LINKS ON PAGE:")
    print("-"*40)
    links = driver.find_elements(By.TAG_NAME, "a")
    for i, link in enumerate(links[:30], 1):
        href = link.get_attribute('href') or ''
        text = link.text.strip()
        if text:
            print(f"   {i}. Text: '{text}'")
            if 'Editor' in text or 'Review' in text or 'Manuscript' in text:
                print(f"      >>> RELEVANT LINK! href: {href[:100]}")

    # Try to find AE Center
    print("\n6. FINDING ASSOCIATE EDITOR CENTER...")
    print("-"*40)

    ae_found = False

    # Method 1: Partial link text
    try:
        ae_link = driver.find_element(By.PARTIAL_LINK_TEXT, "Editor")
        print(f"   ✅ Found AE link: {ae_link.text}")
        ae_link.click()
        time.sleep(5)
        ae_found = True
    except:
        print("   ❌ Method 1 failed")

    # Method 2: Look for specific text
    if not ae_found:
        try:
            ae_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Associate Editor')]")
            print(f"   ✅ Found AE link via XPath: {ae_link.text}")
            ae_link.click()
            time.sleep(5)
            ae_found = True
        except:
            print("   ❌ Method 2 failed")

    # Method 3: Look for any editor-related link
    if not ae_found:
        for link in links:
            if 'editor' in link.text.lower():
                print(f"   Trying: {link.text}")
                link.click()
                time.sleep(5)
                ae_found = True
                break

    if ae_found:
        print("\n7. IN ASSOCIATE EDITOR CENTER")
        print("-"*40)
        print(f"   URL: {driver.current_url}")

        # Look for manuscript counts in page
        page_text = driver.page_source

        # Find anything with MOR- prefix
        mor_pattern = r'MOR-\d{4}-\d{4}'
        mor_matches = re.findall(mor_pattern, page_text)
        if mor_matches:
            print(f"   ✅ FOUND {len(set(mor_matches))} unique manuscript IDs in page:")
            for ms_id in set(mor_matches):
                print(f"      - {ms_id}")

        # Look for category sections
        print("\n8. MANUSCRIPT CATEGORIES/SECTIONS:")
        print("-"*40)

        # Find all table elements
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"   Found {len(tables)} tables")

        # Look for divs with manuscript info
        divs = driver.find_elements(By.TAG_NAME, "div")
        manuscript_divs = []
        for div in divs:
            text = div.text[:100] if div.text else ""
            if "MOR-" in text or "Awaiting" in text or "Review" in text:
                manuscript_divs.append(div)

        print(f"   Found {len(manuscript_divs)} divs with manuscript/category info")

        # Try different methods to find categories
        print("\n9. CATEGORY DETECTION METHODS:")
        print("-"*40)

        # Method A: Look for links with counts
        category_links = []
        for link in driver.find_elements(By.TAG_NAME, "a"):
            text = link.text.strip()
            # Look for patterns like "Awaiting Reviewer Reports (2)"
            if re.search(r'\(\d+\)', text):
                category_links.append((text, link))
                print(f"   Category with count: {text}")

        # Method B: Look for specific sections
        sections = []
        for elem in driver.find_elements(By.XPATH, "//*[contains(text(), 'Awaiting')]"):
            sections.append(elem.text[:100])

        print(f"   Found {len(sections)} elements with 'Awaiting'")

        # Try to click on first category with manuscripts
        print("\n10. ATTEMPTING TO OPEN CATEGORY:")
        print("-"*40)

        if category_links:
            cat_text, cat_link = category_links[0]
            print(f"   Clicking on: {cat_text}")
            try:
                cat_link.click()
                time.sleep(5)

                # Check for manuscripts
                print("\n11. CHECKING FOR MANUSCRIPTS:")
                print("-"*40)

                # Look for MOR- IDs
                page_text = driver.page_source
                mor_matches = re.findall(mor_pattern, page_text)
                if mor_matches:
                    print(f"   ✅ FOUND {len(set(mor_matches))} manuscripts!")
                    for ms_id in set(mor_matches):
                        print(f"      - {ms_id}")

                # Look for manuscript rows
                rows = driver.find_elements(By.TAG_NAME, "tr")
                ms_rows = []
                for row in rows:
                    if "MOR-" in row.text:
                        ms_rows.append(row)

                print(f"   Found {len(ms_rows)} manuscript rows")

                if ms_rows:
                    # Extract details from first manuscript
                    row = ms_rows[0]
                    print(f"\n   FIRST MANUSCRIPT DETAILS:")
                    print("   " + "-"*30)

                    cells = row.find_elements(By.TAG_NAME, "td")
                    for i, cell in enumerate(cells):
                        text = cell.text.strip()[:100]
                        if text:
                            print(f"   Cell {i}: {text}")

                    # Try to find clickable element
                    links_in_row = row.find_elements(By.TAG_NAME, "a")
                    imgs_in_row = row.find_elements(By.TAG_NAME, "img")

                    print(f"   Links in row: {len(links_in_row)}")
                    print(f"   Images in row: {len(imgs_in_row)}")

                    # Click to open manuscript
                    if links_in_row:
                        print("   Clicking first link...")
                        links_in_row[0].click()
                        time.sleep(5)

                        # Check if popup opened
                        if len(driver.window_handles) > 1:
                            print("   ✅ POPUP OPENED")
                            driver.switch_to.window(driver.window_handles[-1])

                            # Extract everything
                            print("\n12. MANUSCRIPT DATA:")
                            print("-"*40)

                            # Get all text
                            body_text = driver.find_element(By.TAG_NAME, "body").text

                            # Extract key info
                            if "Title" in body_text:
                                title_match = re.search(r'Title[:\s]+(.+?)[\n\r]', body_text)
                                if title_match:
                                    print(f"   Title: {title_match.group(1)[:100]}")

                            # Count authors
                            author_count = body_text.count('@')
                            print(f"   Potential authors/referees (@ count): {author_count}")

                            # Look for referee section
                            if "Referee" in body_text or "Reviewer" in body_text:
                                print("   ✅ Found referee section")

                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
            except Exception as e:
                print(f"   Error clicking category: {e}")

        # Show page structure for debugging
        print("\n13. PAGE STRUCTURE DEBUG:")
        print("-"*40)

        # Get main content area
        try:
            main_content = driver.find_element(By.ID, "mainContentArea")
            print("   Found mainContentArea")
            print(f"   Content preview: {main_content.text[:500]}")
        except:
            print("   No mainContentArea found")

        # Look for frame/iframe
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        if frames:
            print(f"   ⚠️ Found {len(frames)} iframes - content might be inside!")
            for i, frame in enumerate(frames):
                print(f"      Frame {i}: {frame.get_attribute('src')[:100] if frame.get_attribute('src') else 'no src'}")

    else:
        print("\n❌ COULD NOT NAVIGATE TO AE CENTER")
        print("   Current page source snippet:")
        print(driver.page_source[:1000])

except Exception as e:
    print(f"\n❌ Fatal error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if driver:
        print("\n" + "="*80)
        print("Keeping browser open for 30 seconds...")
        print("CHECK THE BROWSER WINDOW!")
        time.sleep(30)
        driver.quit()
        print("Browser closed")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)