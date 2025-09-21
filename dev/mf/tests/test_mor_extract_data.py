#!/usr/bin/env python3
"""
MOR EXTRACT DATA - Extract and display referee data
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

from core.gmail_verification import fetch_latest_verification_code

print("="*80)
print("📊 MOR DATA EXTRACTION")
print("="*80)

driver = None
extracted_data = []

try:
    # Setup
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.set_page_load_timeout(60)
    wait = WebDriverWait(driver, 20)

    # Login
    driver.get("https://mc.manuscriptcentral.com/mathor")
    time.sleep(3)

    # Handle cookies
    try:
        reject = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler")))
        reject.click()
        time.sleep(2)
    except:
        pass

    # Login
    wait.until(EC.presence_of_element_located((By.ID, "USERID")))
    driver.find_element(By.ID, "USERID").send_keys(os.getenv('MOR_EMAIL'))
    driver.find_element(By.ID, "PASSWORD").send_keys(os.getenv('MOR_PASSWORD'))

    login_time = time.time()
    driver.find_element(By.ID, "logInButton").click()

    # 2FA
    time.sleep(5)
    if "TOKEN_VALUE" in driver.page_source:
        print("🔐 Handling 2FA...")
        time.sleep(15)

        code = fetch_latest_verification_code(
            'MOR',
            max_wait=60,
            poll_interval=3,
            start_timestamp=login_time + 5
        )

        if code:
            driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
            driver.execute_script("document.getElementById('VERIFY_BTN').click();")
            time.sleep(10)

    print("✅ Logged in\n")

    # Navigate to AE Center
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if "associate editor" in link.text.lower():
            driver.execute_script("arguments[0].click();", link)
            time.sleep(5)
            break

    # Go to Awaiting Reviewer Reports
    for link in driver.find_elements(By.TAG_NAME, "a"):
        if "Awaiting Reviewer Reports" in link.text:
            driver.execute_script("arguments[0].click();", link)
            time.sleep(5)
            break

    # Process manuscripts
    manuscript_rows = driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
    print(f"📋 Found {len(manuscript_rows)} manuscripts\n")

    # Process first manuscript only for quick demo
    if manuscript_rows:
        row = manuscript_rows[0]
        row_text = row.text

        # Extract ID
        mor_match = re.search(r'MOR-\d{4}-\d+', row_text)
        manuscript_id = mor_match.group() if mor_match else "Unknown"

        # Extract table summary
        lines = row_text.split('\n')
        table_summary = ""
        for line in lines:
            if any(word in line for word in ['active', 'invited', 'agreed', 'declined', 'returned']):
                table_summary = line
                break

        print(f"🔍 Processing {manuscript_id}")
        print(f"   Table summary: {table_summary}\n")

        # Click manuscript - try ID link or action image
        action_button = None
        try:
            action_button = row.find_element(By.XPATH, f".//a[contains(text(), '{manuscript_id}')]")
        except:
            try:
                action_button = row.find_element(By.XPATH,
                    ".//img[contains(@src, 'check') or contains(@src, 'action')]/parent::*")
            except:
                pass

        if action_button:
            original_url = driver.current_url
            driver.execute_script("arguments[0].scrollIntoView(true);", action_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", action_button)
            time.sleep(5)

            # Check if navigated
            if driver.current_url != original_url:
                print("✅ Navigated to manuscript details\n")

                # Extract manuscript data
                manuscript_data = {
                    "manuscript_id": manuscript_id,
                    "title": "",
                    "authors": [],
                    "referees": []
                }

                # Extract title
                try:
                    # Look for title in various places
                    title_patterns = [
                        "//td[contains(text(), 'Title')]/following-sibling::td",
                        "//div[contains(@class, 'title')]",
                        "//h2[contains(@class, 'manuscript')]"
                    ]
                    for pattern in title_patterns:
                        try:
                            title_elem = driver.find_element(By.XPATH, pattern)
                            if title_elem.text:
                                manuscript_data["title"] = title_elem.text
                                break
                        except:
                            pass

                    # If not found, extract from page text
                    if not manuscript_data["title"]:
                        # Look for title after manuscript ID
                        page_text = driver.page_source
                        title_match = re.search(f'{manuscript_id}.*?Submitted.*?\n(.*?)\n', page_text)
                        if title_match:
                            manuscript_data["title"] = title_match.group(1)

                except:
                    pass

                # Extract referee data
                print("👥 REFEREE DATA:")
                print("-" * 40)

                # Debug: See what's on the page
                all_rows = driver.find_elements(By.TAG_NAME, "tr")
                print(f"Debug: Found {len(all_rows)} total TR elements on page")

                # Look for rows with referee indicators
                referee_rows = []
                for row in all_rows:
                    row_text = row.text
                    # Check if this looks like a referee row
                    if row_text and any(status in row_text for status in ['Invited:', 'Agreed :', 'Declined :', 'Agreed:', 'Declined:']):
                        referee_rows.append(row)

                print(f"Debug: Found {len(referee_rows)} referee rows")

                for i, ref_row in enumerate(referee_rows[:20]):  # Limit to first 20
                    try:
                        cells = ref_row.find_elements(By.TAG_NAME, "td")
                        if len(cells) > 2:
                            # Extract name (usually 2nd cell)
                            name = cells[1].text.strip() if cells[1].text else ""

                            # Skip if it's not a referee row
                            if not name or name in ['Name', 'Order', ''] or 'Reviewer List' in name:
                                continue

                            # Extract status (usually 3rd cell)
                            status = cells[2].text.strip() if cells[2].text else ""

                            # Extract dates if available
                            dates = {}
                            row_text = ref_row.text

                            # Look for date patterns
                            invited_match = re.search(r'Invited:\s*(\d{2}-\w{3}-\d{4})', row_text)
                            if invited_match:
                                dates['invited'] = invited_match.group(1)

                            agreed_match = re.search(r'Agreed\s*:\s*(\d{2}-\w{3}-\d{4})', row_text)
                            if agreed_match:
                                dates['agreed'] = agreed_match.group(1)

                            declined_match = re.search(r'Declined\s*:\s*(\d{2}-\w{3}-\d{4})', row_text)
                            if declined_match:
                                dates['declined'] = declined_match.group(1)

                            due_match = re.search(r'Due Date:\s*(\d{2}-\w{3}-\d{4})', row_text)
                            if due_match:
                                dates['due'] = due_match.group(1)

                            # Extract email if available
                            email = ""
                            try:
                                email_link = ref_row.find_element(By.XPATH, ".//a[contains(@href, 'mailto')]")
                                email_href = email_link.get_attribute('href')
                                if email_href:
                                    email = email_href.replace('mailto:', '')
                            except:
                                pass

                            referee_info = {
                                "name": name,
                                "status": status,
                                "dates": dates,
                                "email": email
                            }

                            manuscript_data["referees"].append(referee_info)

                            # Display referee info
                            print(f"\nReferee {len(manuscript_data['referees'])}:")
                            print(f"   Name: {name}")
                            print(f"   Status: {status}")
                            if dates:
                                for key, value in dates.items():
                                    print(f"   {key.capitalize()}: {value}")
                            if email:
                                print(f"   Email: {email}")

                    except Exception as e:
                        continue

                # Save data
                extracted_data.append(manuscript_data)

                print("\n" + "="*40)
                print(f"✅ Extracted {len(manuscript_data['referees'])} referees")
                if manuscript_data['title']:
                    print(f"📄 Title: {manuscript_data['title'][:80]}...")

    # Save to file
    output_file = f"/tmp/mor_extracted_data_{int(time.time())}.json"
    with open(output_file, "w") as f:
        json.dump(extracted_data, f, indent=2)

    print(f"\n💾 Data saved to: {output_file}")

    # Print summary
    print("\n" + "="*60)
    print("📊 EXTRACTION SUMMARY")
    print("="*60)
    for manuscript in extracted_data:
        print(f"\nManuscript: {manuscript['manuscript_id']}")
        if manuscript['title']:
            print(f"Title: {manuscript['title'][:60]}...")
        print(f"Referees: {len(manuscript['referees'])}")

        # Count by status
        status_counts = {}
        for ref in manuscript['referees']:
            status = ref['status'] or 'Unknown'
            status_counts[status] = status_counts.get(status, 0) + 1

        for status, count in status_counts.items():
            print(f"  - {status}: {count}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

finally:
    if driver:
        print("\n🔚 Closing browser...")
        driver.quit()

print("\n" + "="*80)
print("DATA EXTRACTION COMPLETE")
print("="*80)