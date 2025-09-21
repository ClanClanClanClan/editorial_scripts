#!/usr/bin/env python3
"""
Debug script to understand referee table structure on both manuscripts
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


def debug_referee_tables():
    """Debug referee table structure on both manuscripts"""
    print("🔍 Debugging referee table structures...")

    extractor = ComprehensiveMFExtractor()

    try:
        # Login
        print("📝 Logging in...")
        if not extractor.login():
            print("❌ Login failed")
            return

        # Navigate to AE Center
        print("🏠 Navigating to AE Center...")
        if not extractor.navigate_to_ae_center():
            print("❌ Navigation to AE Center failed")
            return

        # Find categories
        print("📋 Finding categories...")
        categories = extractor.get_categories()

        # Find "Awaiting Reviewer Scores" category
        target_category = None
        for category in categories:
            if "Awaiting Reviewer Scores" in category["name"] and category["count"] >= 2:
                target_category = category
                break

        if not target_category:
            print("❌ No suitable category found")
            return

        print(
            f"🎯 Processing category: {target_category['name']} ({target_category['count']} manuscripts)"
        )

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

        # Debug manuscript 1
        print(f"\n🔍 MANUSCRIPT 1: {manuscript_order[0]}")
        debug_single_manuscript(extractor)

        # Navigate to manuscript 2
        print("\n➡️ Navigating to manuscript 2...")
        extractor.click_next_document()
        time.sleep(3)

        # Debug manuscript 2
        print(f"\n🔍 MANUSCRIPT 2: {manuscript_order[1]}")
        debug_single_manuscript(extractor)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        if hasattr(extractor, "driver") and extractor.driver:
            extractor.driver.quit()


def debug_single_manuscript(extractor):
    """Debug referee table structure on current manuscript"""
    driver = extractor.driver

    # Get manuscript ID
    manuscript_id = extractor.get_current_manuscript_id()
    print(f"   Manuscript ID: {manuscript_id}")

    # Find ALL rows with mailpopup links
    all_mailpopup_rows = driver.find_elements(By.XPATH, "//tr[.//a[contains(@href,'mailpopup')]]")
    print(f"   Total rows with mailpopup links: {len(all_mailpopup_rows)}")

    # Debug each row
    for i, row in enumerate(all_mailpopup_rows):
        print(f"\n   Row {i+1}:")
        row_text = row.text.replace("\n", " | ")
        print(f"      Text: {row_text[:200]}...")

        # Check for editorial keywords
        editorial_keywords = [
            "Admin:",
            "Editor-in-Chief:",
            "Co-Editor:",
            "Associate Editor:",
            "Submitting Author:",
            "Authors & Institutions:",
        ]

        found_keywords = [kw for kw in editorial_keywords if kw in row_text]
        if found_keywords:
            print(f"      ⚠️ Editorial keywords found: {found_keywords}")
        else:
            print("      ✅ No editorial keywords found")

        # Try to extract email
        try:
            mailpopup_link = row.find_element(By.XPATH, ".//a[contains(@href,'mailpopup')]")
            onclick = mailpopup_link.get_attribute("onclick")
            if "mailpopup" in onclick:
                email_start = onclick.find("'") + 1
                email_end = onclick.find("'", email_start)
                email = onclick[email_start:email_end]
                print(f"      Email: {email}")
        except:
            print("      Email: [couldn't extract]")

    # Also check the specific XPath patterns
    print("\n   Testing specific XPath patterns:")

    # Pattern 1: tablelines
    tablelines_rows = driver.find_elements(
        By.XPATH, "//td[@class='tablelines']//tr[.//a[contains(@href,'mailpopup')]]"
    )
    print(f"   Rows in tablelines: {len(tablelines_rows)}")

    # Pattern 2: tablelines + tablelightcolor
    light_rows = driver.find_elements(
        By.XPATH,
        "//td[@class='tablelines']//tr[td[@class='tablelightcolor'] and .//a[contains(@href,'mailpopup')]]",
    )
    print(f"   Rows with tablelightcolor: {len(light_rows)}")

    # Pattern 3: Check for referee status text
    status_texts = ["Agreed", "Declined", "Invited", "Unavailable", "Completed"]
    for status in status_texts:
        status_rows = driver.find_elements(
            By.XPATH, f"//tr[contains(., '{status}') and .//a[contains(@href,'mailpopup')]]"
        )
        if status_rows:
            print(f"   Rows with status '{status}': {len(status_rows)}")


if __name__ == "__main__":
    debug_referee_tables()
