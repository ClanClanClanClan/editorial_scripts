#!/usr/bin/env python3
"""
Debug why referee extraction fails on second manuscript
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


def debug_second_manuscript():
    """Debug referee extraction on second manuscript"""
    print("🔍 Debugging second manuscript referee extraction...")

    extractor = ComprehensiveMFExtractor()

    try:
        # Run extraction until we get to Pass 1
        print("\n📝 Running extraction to get to manuscripts...")

        # Login
        if not extractor.login():
            print("❌ Login failed")
            return

        # Navigate to AE Center
        if not extractor.navigate_to_ae_center():
            print("❌ Navigation to AE Center failed")
            return

        # Get categories
        categories = extractor.get_manuscript_categories()

        # Find "Awaiting Reviewer Scores" category
        target_category = None
        for category in categories:
            if "Awaiting Reviewer Scores" in category["name"] and category["count"] >= 2:
                target_category = category
                break

        if not target_category:
            print("❌ No suitable category found")
            return

        # Click category
        target_category["link"].click()
        time.sleep(3)

        # Click first Take Action
        take_action_links = extractor.driver.find_elements(
            By.XPATH, "//a[contains(@href,'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]"
        )

        if len(take_action_links) < 2:
            print("❌ Need at least 2 manuscripts")
            return

        take_action_links[0].click()
        time.sleep(5)

        # Get manuscript info
        (
            manuscript_count,
            manuscript_data,
            manuscript_order,
        ) = extractor.extract_basic_manuscript_info()

        print(f"\n📄 Found {manuscript_count} manuscripts: {manuscript_order}")

        # Navigate to second manuscript
        print("\n➡️ Navigating to second manuscript...")
        extractor.click_next_document()

        # Verify we're on second manuscript
        current_id = extractor.get_current_manuscript_id()
        print(f"   Current manuscript: {current_id}")

        if current_id != manuscript_order[1]:
            print(f"   ❌ Expected {manuscript_order[1]}, got {current_id}")

        # Debug referee extraction
        print("\n🔍 Debugging referee table structure...")

        # Find ALL rows with mailpopup links
        all_mailpopup_rows = extractor.driver.find_elements(
            By.XPATH, "//tr[.//a[contains(@href,'mailpopup')]]"
        )
        print(f"   Total rows with mailpopup links: {len(all_mailpopup_rows)}")

        # Show each row
        for i, row in enumerate(all_mailpopup_rows[:10]):  # Show first 10
            row_text = row.text.replace("\n", " | ")
            print(f"\n   Row {i+1}: {row_text[:150]}...")

        # Test the actual extraction XPath
        print("\n🔍 Testing actual extraction XPath...")

        # First, get all rows
        all_referee_rows = extractor.driver.find_elements(
            By.XPATH,
            "//td[@class='tablelines']//tr[td[@class='tablelightcolor'] and .//a[contains(@href,'mailpopup')]]",
        )
        print(f"   All referee rows found: {len(all_referee_rows)}")

        # Check what filtering removes
        print("\n🔍 Testing filtering logic...")
        editorial_keywords = [
            "Admin:",
            "Editor-in-Chief:",
            "Co-Editor:",
            "Associate Editor:",
            "Submitting Author:",
            "Authors & Institutions:",
            "Executive Editor:",
            "Managing Editor:",
            "Guest Editor:",
        ]

        filtered_count = 0
        for row in all_referee_rows:
            row_text = row.text
            is_editorial = False

            for keyword in editorial_keywords:
                if keyword in row_text:
                    is_editorial = True
                    print(f"   ❌ Filtered out row with '{keyword}': {row_text[:100]}...")
                    break

            if not is_editorial:
                # Check author emails
                if any(
                    email in row_text
                    for email in [
                        "wguanchen@sdu.edu.cn",
                        "maxu@polyu.edu.hk",
                        "15253166207@163.com",
                    ]
                ):
                    print(f"   ❌ Filtered out row with author email: {row_text[:100]}...")
                else:
                    filtered_count += 1
                    print(f"   ✅ Valid referee row {filtered_count}: {row_text[:100]}...")

        print(f"\n📊 Summary: {len(all_referee_rows)} total rows, {filtered_count} after filtering")

        # Check specific table structure
        print("\n🔍 Checking table structure...")
        tablelines = extractor.driver.find_elements(By.CLASS_NAME, "tablelines")
        print(f"   Found {len(tablelines)} elements with class 'tablelines'")

        tablelightcolor = extractor.driver.find_elements(By.CLASS_NAME, "tablelightcolor")
        print(f"   Found {len(tablelightcolor)} elements with class 'tablelightcolor'")

        # Save page source
        print("\n💾 Saving page source...")
        with open("debug_second_manuscript_page.html", "w") as f:
            f.write(extractor.driver.page_source)
        print("   ✅ Saved to debug_second_manuscript_page.html")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("\n🔚 Debug complete. Browser will stay open for 20 seconds...")
        time.sleep(20)
        if hasattr(extractor, "driver") and extractor.driver:
            extractor.driver.quit()


if __name__ == "__main__":
    debug_second_manuscript()
