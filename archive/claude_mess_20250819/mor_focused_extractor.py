#!/usr/bin/env python3
"""
FOCUSED MOR Extractor - Extract the 2 manuscripts efficiently
"""

import json
import os
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.gmail_verification_wrapper import fetch_latest_verification_code


def extract_mor_manuscripts():
    """Extract MOR-2025-1136 and MOR-2025-1037."""

    # Setup Chrome
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)

    manuscripts = []
    processed_ids = set()

    try:
        # Login
        print("🔐 FOCUSED Login...")
        driver.get("https://mc.manuscriptcentral.com/mathor")
        time.sleep(5)

        email = os.getenv("MOR_EMAIL", "dylan.possamai@math.ethz.ch")
        password = os.getenv("MOR_PASSWORD", "")

        # Enter credentials
        email_field = wait.until(EC.element_to_be_clickable((By.ID, "USERID")))
        email_field.send_keys(email)
        driver.find_element(By.ID, "PASSWORD").send_keys(password)
        driver.find_element(By.ID, "logInButton").click()
        time.sleep(5)

        # Handle 2FA if needed
        if "twoFactorAuthForm" in driver.page_source:
            print("   📱 2FA required...")
            login_time = datetime.now()
            code = fetch_latest_verification_code(
                "MOR", max_wait=30, poll_interval=2, start_timestamp=login_time
            )
            if code:
                print(f"   ✅ Got code: {code[:3]}***")
                driver.find_element(By.NAME, "verificationCode").send_keys(code)
                driver.find_element(By.ID, "submitButton").click()
                time.sleep(5)

        # Check for device verification
        if (
            "Unrecognized Device" in driver.page_source
            or "verification code" in driver.page_source.lower()
        ):
            print("   🔐 Device verification required...")
            device_time = datetime.now()
            device_code = fetch_latest_verification_code(
                "MOR", max_wait=30, poll_interval=2, start_timestamp=device_time
            )

            if device_code:
                print(f"   ✅ Got device code: {device_code[:3]}***")

                # Find any text input field
                input_fields = driver.find_elements(By.XPATH, "//input[@type='text']")
                if input_fields:
                    input_fields[0].send_keys(device_code)
                    time.sleep(1)

                    # Try to submit
                    submit_buttons = driver.find_elements(
                        By.XPATH,
                        "//a[contains(text(), 'Verify')] | //button[contains(text(), 'Verify')] | //input[@type='submit']",
                    )
                    if submit_buttons:
                        submit_buttons[0].click()
                    else:
                        input_fields[0].send_keys("\n")  # Try Enter key

                    time.sleep(5)
                    print("   ✅ Device verification attempted")

        current_url = driver.current_url
        print(f"   📍 Current URL: {current_url}")

        # Try direct AE Dashboard navigation
        print("\n📋 Direct AE Dashboard navigation...")
        ae_url = "https://mc.manuscriptcentral.com/mathor?NEXT_PAGE=ASSOCIATE_EDITOR_DASHBOARD"
        driver.get(ae_url)
        time.sleep(5)

        # Debug current page
        page_text = driver.find_element(By.TAG_NAME, "body").text[:300]
        print(f"   📄 Page content: {page_text[:100]}...")

        # Look for navigation elements
        if "Mathematics of Operations Research" in page_text:
            print("   ✅ Found journal context")

        # Try to find AE Center or categories directly
        category_found = False
        category_selectors = [
            "//a[contains(text(), 'Awaiting Reviewer Reports')]",
            "//a[contains(text(), 'Associate Editor')]",
            "//a[contains(text(), 'Categories')]",
        ]

        for selector in category_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                if elements:
                    print(f"   ✅ Found category element: {elements[0].text}")
                    if "Awaiting" in elements[0].text:
                        elements[0].click()
                        category_found = True
                        time.sleep(5)
                        break
                    elif "Associate Editor" in elements[0].text:
                        elements[0].click()
                        time.sleep(5)
                        # Now look for Awaiting category
                        awaiting_links = driver.find_elements(
                            By.XPATH, "//a[contains(text(), 'Awaiting Reviewer Reports')]"
                        )
                        if awaiting_links:
                            awaiting_links[0].click()
                            category_found = True
                            time.sleep(5)
                            break
            except Exception as e:
                print(f"   ⚠️ Category navigation error: {e}")
                continue

        if not category_found:
            print("   ❌ Could not find category, trying manual page inspection...")
            # Save page for debugging
            with open("mor_focused_debug.html", "w") as f:
                f.write(driver.page_source)
            print("   💾 Saved page for debugging")

            # Look for any manuscript-related links
            links = driver.find_elements(By.TAG_NAME, "a")
            manuscript_links = [
                link
                for link in links
                if link.text and ("MOR" in link.text or "manuscript" in link.text.lower())
            ]
            if manuscript_links:
                print(f"   📄 Found {len(manuscript_links)} potential manuscript links")
                for link in manuscript_links[:3]:
                    print(f"      - {link.text}")

        if category_found or True:  # Continue even if category not explicitly found
            print("\n📊 Looking for manuscripts in current page...")

            # Look for Take Action buttons
            take_action_images = driver.find_elements(
                By.XPATH, "//img[contains(@src, 'check_off.gif')]"
            )
            print(f"   Found {len(take_action_images)} Take Action buttons")

            # Get manuscript rows
            manuscript_rows = []
            for img in take_action_images:
                try:
                    row = img.find_element(By.XPATH, "./ancestor::tr[1]")
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        manuscript_id = cells[0].text.strip()
                        if manuscript_id and "MOR-" in manuscript_id:
                            manuscript_rows.append((manuscript_id, row, img))
                            print(f"   📄 Found manuscript: {manuscript_id}")
                except Exception as e:
                    print(f"   ⚠️ Row processing error: {e}")

            print(f"\n✅ FOUND {len(manuscript_rows)} MOR MANUSCRIPTS")

            # Process each manuscript
            for i, (manuscript_id, row, take_action_img) in enumerate(manuscript_rows):
                if manuscript_id in processed_ids:
                    print(f"   ⏭️ Skipping {manuscript_id} - already processed")
                    continue

                print(f"\n📄 Processing {i+1}/{len(manuscript_rows)}: {manuscript_id}")

                try:
                    # Click Take Action
                    original_window = driver.current_window_handle
                    take_action_link = take_action_img.find_element(By.XPATH, "./parent::a")
                    take_action_link.click()
                    time.sleep(5)

                    # Extract basic data
                    manuscript_data = {
                        "id": manuscript_id,
                        "title": "",
                        "authors": [],
                        "referees": [],
                        "extracted_at": datetime.now().isoformat(),
                    }

                    # Get title
                    try:
                        title_elem = driver.find_element(
                            By.XPATH, "//td[contains(text(), 'Title:')]/following-sibling::td"
                        )
                        manuscript_data["title"] = title_elem.text.strip()
                        print(f"   📄 Title: {manuscript_data['title'][:50]}...")
                    except:
                        print("   ⚠️ Could not extract title")

                    # Get basic referees (safe extraction)
                    try:
                        referee_links = driver.find_elements(
                            By.XPATH,
                            "//a[contains(@href, 'referee') or contains(text(), 'Reviewer')]",
                        )[:3]
                        for link in referee_links:
                            referee_name = link.text.strip()
                            if referee_name and len(referee_name) > 3:
                                manuscript_data["referees"].append({"name": referee_name})
                        print(f"   👥 Found {len(manuscript_data['referees'])} referees")
                    except:
                        print("   ⚠️ Could not extract referees")

                    manuscripts.append(manuscript_data)
                    processed_ids.add(manuscript_id)
                    print(f"   ✅ Successfully processed {manuscript_id}")

                    # Cleanup popups
                    try:
                        all_windows = driver.window_handles
                        if len(all_windows) > 1:
                            for window in all_windows:
                                if window != original_window:
                                    driver.switch_to.window(window)
                                    driver.close()
                            driver.switch_to.window(original_window)
                    except:
                        pass

                    # Go back
                    driver.back()
                    time.sleep(3)

                except Exception as e:
                    print(f"   ❌ Processing error for {manuscript_id}: {e}")
                    try:
                        driver.switch_to.window(original_window)
                        driver.back()
                        time.sleep(2)
                    except:
                        pass

        # Save results
        output = {
            "extraction_time": datetime.now().isoformat(),
            "manuscripts": manuscripts,
            "total_unique": len(processed_ids),
            "processed_ids": list(processed_ids),
        }

        with open("mor_focused_results.json", "w") as f:
            json.dump(output, f, indent=2)

        print("\n🎉 FOCUSED EXTRACTION COMPLETE!")
        print(f"   📊 Total manuscripts: {len(manuscripts)}")
        print(f"   📋 IDs: {list(processed_ids)}")

        for manuscript in manuscripts:
            print(f"   ✅ {manuscript['id']}: {manuscript['title'][:50]}...")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()

        # Save debug info
        try:
            with open("mor_focused_error.html", "w") as f:
                f.write(driver.page_source)
            print("💾 Saved error page for debugging")
        except:
            pass

    finally:
        input("\n⏸️ Press Enter to close browser...")
        driver.quit()

    return manuscripts


if __name__ == "__main__":
    results = extract_mor_manuscripts()
    print(f"\n📊 FINAL: {len(results)} manuscripts extracted")
