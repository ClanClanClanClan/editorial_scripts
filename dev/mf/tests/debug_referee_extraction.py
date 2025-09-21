#!/usr/bin/env python3
"""
Debug referee extraction in MOR
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from extractors.mor_extractor import MORExtractor
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

print("="*60)
print("🔬 DEBUGGING REFEREE EXTRACTION")
print("="*60)

mor = None
try:
    # Create and initialize
    print("\n1️⃣ Setting up MOR...")
    mor = MORExtractor(use_cache=False)
    mor.driver = webdriver.Chrome(options=mor.chrome_options)
    mor.driver.set_page_load_timeout(30)
    mor.driver.implicitly_wait(10)
    mor.wait = WebDriverWait(mor.driver, 10)
    mor.original_window = mor.driver.current_window_handle
    print("   ✅ Setup complete")

    # Login
    print("\n2️⃣ Logging in...")
    if not mor.login():
        raise Exception("Login failed")
    print("   ✅ Login successful")

    # Navigate
    print("\n3️⃣ Navigating to AE Center...")
    if not mor.navigate_to_ae_center():
        raise Exception("Navigation failed")
    print("   ✅ In AE Center")

    # Find a category with manuscripts
    print("\n4️⃣ Looking for manuscripts...")
    category = "Awaiting Reviewer Reports"

    try:
        category_link = mor.driver.find_element(By.LINK_TEXT, category)
        mor.safe_click(category_link)
        mor.smart_wait(3)
        print(f"   ✅ Clicked on '{category}'")
    except:
        print(f"   ❌ Could not find category '{category}'")
        # Try to find any category
        links = mor.driver.find_elements(By.XPATH, "//a[contains(text(), 'Awaiting') or contains(text(), 'Overdue')]")
        if links:
            print(f"   Found {len(links)} alternative links")
            mor.safe_click(links[0])
            mor.smart_wait(3)

    # Find manuscripts
    manuscript_rows = mor.driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
    print(f"\n5️⃣ Found {len(manuscript_rows)} manuscripts")

    if manuscript_rows:
        # Click on first manuscript
        row = manuscript_rows[0]
        row_text = mor.safe_get_text(row)
        print(f"   First manuscript: {row_text[:80]}...")

        # Find and click check icon
        try:
            check_icon = row.find_element(By.XPATH, ".//img[contains(@src, 'check')]")
            parent_link = check_icon.find_element(By.XPATH, "./parent::*")
            mor.safe_click(parent_link)
            mor.smart_wait(3)
            print("   ✅ Clicked on manuscript")
        except:
            # Alternative: click on manuscript ID
            ms_link = row.find_element(By.XPATH, ".//a[contains(text(), 'MOR-')]")
            mor.safe_click(ms_link)
            mor.smart_wait(3)
            print("   ✅ Clicked on manuscript ID")

        # Check current page
        print("\n6️⃣ Analyzing current page...")
        page_title = mor.driver.title
        print(f"   Page title: {page_title}")

        # Look for tabs
        all_links = mor.driver.find_elements(By.TAG_NAME, "a")
        tab_keywords = ['Referee', 'Reviewer', 'Review', 'Editor', 'Decision', 'Manuscript', 'Author']
        relevant_links = []

        for link in all_links:
            link_text = mor.safe_get_text(link)
            if link_text and any(keyword in link_text for keyword in tab_keywords):
                relevant_links.append(link_text)

        print(f"   Found {len(relevant_links)} relevant links:")
        for i, text in enumerate(relevant_links[:10]):
            print(f"      {i+1}. {text}")

        # Navigate to referee tab specifically
        print("\n7️⃣ Looking for Referee/Reviewer tab...")
        referee_tab = None

        # Try different selectors
        selectors = [
            "//a[contains(text(), 'Referee')]",
            "//a[contains(text(), 'Reviewer')]",
            "//a[contains(text(), 'Review')]",
            "//a[contains(@href, 'TAB_REVIEWER')]",
            "//a[contains(@href, 'referee')]"
        ]

        for selector in selectors:
            try:
                elements = mor.driver.find_elements(By.XPATH, selector)
                if elements:
                    referee_tab = elements[0]
                    tab_text = mor.safe_get_text(referee_tab)
                    print(f"   Found tab: '{tab_text}'")
                    break
            except:
                continue

        if referee_tab:
            mor.safe_click(referee_tab)
            mor.smart_wait(3)
            print("   ✅ Clicked referee tab")

            # Now look for referee data
            print("\n8️⃣ Analyzing referee data...")

            # Check page source for referee indicators
            page_source = mor.driver.page_source
            referee_keywords = ['Declined', 'Agreed', 'Invited', 'Pending', 'Overdue', 'Complete', 'Referee', 'Reviewer']

            for keyword in referee_keywords:
                count = page_source.count(keyword)
                if count > 0:
                    print(f"   Found '{keyword}': {count} occurrences")

            # Look for referee rows more broadly
            print("\n9️⃣ Looking for referee rows...")

            # Try different approaches
            approaches = [
                ("Table rows with status", "//tr[contains(., 'Declined') or contains(., 'Agreed') or contains(., 'Invited')]"),
                ("Any element with status", "//*[contains(text(), 'Declined') or contains(text(), 'Agreed') or contains(text(), 'Invited')]"),
                ("Links with mailpopup", "//a[contains(@href, 'mailpopup')]"),
                ("Links with popup", "//a[contains(@href, 'popup')]"),
                ("Table cells with email", "//td[contains(., '@')]")
            ]

            for description, xpath in approaches:
                elements = mor.driver.find_elements(By.XPATH, xpath)
                if elements:
                    print(f"   {description}: Found {len(elements)} elements")
                    for i, elem in enumerate(elements[:3]):
                        text = mor.safe_get_text(elem)[:100]
                        if text:
                            print(f"      {i+1}. {text}")

            # Try to extract referee data directly
            print("\n🔟 Attempting direct extraction...")
            referee_data = mor.extract_referee_details()
            print(f"   Extracted {len(referee_data)} referees")

            for i, referee in enumerate(referee_data[:3]):
                print(f"\n   Referee {i+1}:")
                for key, value in referee.items():
                    if value:
                        print(f"      {key}: {value}")

        else:
            print("   ❌ Could not find referee tab")

    else:
        print("   ❌ No manuscripts found")

except KeyboardInterrupt:
    print("\n⚠️ Interrupted by user")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if mor and hasattr(mor, 'driver'):
        try:
            mor.driver.quit()
            print("\n🧹 Driver closed")
        except:
            pass
    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)