#!/usr/bin/env python3
"""
Simple test with minimal referee extraction - no popups, no complex processing
"""

import sys
import time
from pathlib import Path

# Add path to import the MF extractor
sys.path.append(str(Path(__file__).parent.parent))

# Import credentials
try:
    from ensure_credentials import load_credentials

    load_credentials()
except ImportError:
    from dotenv import load_dotenv

    load_dotenv(".env.production")

from mf_extractor import ComprehensiveMFExtractor
from selenium.webdriver.common.by import By


def extract_referees_simple(driver, manuscript_id):
    """Simple referee extraction without popups or complex processing"""
    print(f"   🔍 Simple referee extraction for {manuscript_id}...")

    # Find all referee rows
    all_referee_rows = driver.find_elements(
        By.XPATH,
        "//td[@class='tablelines']//tr[td[@class='tablelightcolor'] and .//a[contains(@href,'mailpopup')]]",
    )

    print(f"      Found {len(all_referee_rows)} total rows with mailpopup links")

    # Simple filtering - just remove obvious editorial staff
    editorial_keywords = ["Admin:", "Editor-in-Chief:", "Associate Editor:", "Submitting Author:"]

    referee_count = 0
    for i, row in enumerate(all_referee_rows):
        row_text = row.text

        # Skip editorial staff
        is_editorial = any(keyword in row_text for keyword in editorial_keywords)

        # Skip manuscript authors
        is_author = any(
            email in row_text
            for email in ["wguanchen@sdu.edu.cn", "maxu@polyu.edu.hk", "15253166207@163.com"]
        )

        if not is_editorial and not is_author:
            try:
                # Just get the name from the link
                name_link = row.find_element(By.XPATH, ".//a[contains(@href,'mailpopup')]")
                name = name_link.text.strip()
                print(f"         Referee {referee_count + 1}: {name}")
                referee_count += 1
            except:
                pass
        else:
            print(f"         Filtered out row {i+1}: {'Editorial' if is_editorial else 'Author'}")

    print(f"      Simple extraction found {referee_count} referees")
    return referee_count


def simple_test():
    """Simple focused test"""
    print("🎯 SIMPLE REFEREE TEST")

    extractor = ComprehensiveMFExtractor()

    try:
        # Login and navigate (this works)
        if not extractor.login():
            print("❌ Login failed")
            return False

        if not extractor.navigate_to_ae_center():
            print("❌ Navigation failed")
            return False

        # Get to manuscripts
        categories = extractor.get_manuscript_categories()
        target_category = None
        for category in categories:
            if "Awaiting Reviewer Scores" in category["name"]:
                target_category = category
                break

        target_category["link"].click()
        time.sleep(3)

        take_action_links = extractor.driver.find_elements(
            By.XPATH, "//a[contains(@href,'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]"
        )
        take_action_links[0].click()
        time.sleep(5)

        # Get manuscript order
        (
            manuscript_count,
            manuscript_data,
            manuscript_order,
        ) = extractor.extract_basic_manuscript_info()
        print(f"📄 Found manuscripts: {manuscript_order}")

        # Test manuscript 1
        print(f"\n📄 Testing manuscript 1: {manuscript_order[0]}")
        current_id = extractor.get_current_manuscript_id()
        print(f"   Current page: {current_id}")
        referees_1 = extract_referees_simple(extractor.driver, manuscript_order[0])

        # Navigate to manuscript 2
        print("\n➡️ Navigating to manuscript 2...")
        extractor.click_next_document()

        # Test manuscript 2
        print(f"\n📄 Testing manuscript 2: {manuscript_order[1]}")
        current_id = extractor.get_current_manuscript_id()
        print(f"   Current page: {current_id}")
        referees_2 = extract_referees_simple(extractor.driver, manuscript_order[1])

        # Results
        total = referees_1 + referees_2
        print("\n📊 RESULTS:")
        print(f"   Manuscript 1: {referees_1} referees")
        print(f"   Manuscript 2: {referees_2} referees")
        print(f"   Total: {total} referees")

        if total == 6:
            print("✅ SUCCESS: Found all 6 referees!")
            return True
        else:
            print(f"❌ FAIL: Expected 6, got {total}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        if hasattr(extractor, "driver") and extractor.driver:
            extractor.driver.quit()


if __name__ == "__main__":
    success = simple_test()
    print(f"\n🎯 RESULT: {'SUCCESS' if success else 'FAILURE'}")
    sys.exit(0 if success else 1)
