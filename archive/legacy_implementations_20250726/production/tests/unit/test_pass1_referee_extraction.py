#!/usr/bin/env python3
"""
Test ONLY Pass 1 referee extraction to verify it works for both manuscripts
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


def test_pass1_only():
    """Test only Pass 1 referee extraction"""
    print("🧪 Testing Pass 1 referee extraction ONLY...")

    extractor = ComprehensiveMFExtractor()

    try:
        # Login
        print("\n📝 Logging in...")
        if not extractor.login():
            print("❌ Login failed")
            return

        # Navigate to AE Center
        print("\n🏠 Navigating to AE Center...")
        if not extractor.navigate_to_ae_center():
            print("❌ Navigation to AE Center failed")
            return

        # Find categories
        print("\n📋 Finding categories...")
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

        print(
            f"\n🎯 Processing category: {target_category['name']} ({target_category['count']} manuscripts)"
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

        # ONLY RUN PASS 1
        print(f"\n🔬 TESTING PASS 1 ONLY: Main pages forward (1 → {manuscript_count})")
        print("=" * 60)

        extractor.extract_main_pages_forward(manuscript_count, manuscript_data, manuscript_order)

        print("\n" + "=" * 60)
        print("📊 PASS 1 RESULTS:")
        print("=" * 60)

        total_referees = 0
        for i, manuscript_id in enumerate(manuscript_order[:2]):
            manuscript = manuscript_data[manuscript_id]
            referee_count = len(manuscript.get("referees", []))
            total_referees += referee_count

            print(f"\n📄 Manuscript {i+1}: {manuscript_id}")
            print(f"   Title: {manuscript.get('title', 'Unknown')[:60]}...")
            print(f"   Status: {manuscript.get('status', 'Unknown')}")
            print(f"   Referees found: {referee_count}")

            if referee_count > 0:
                for j, referee in enumerate(manuscript["referees"]):
                    print(f"      {j+1}. {referee.get('name')} - {referee.get('status')}")
            else:
                print("   ❌ NO REFEREES EXTRACTED!")

        print(f"\n📊 TOTAL REFEREES: {total_referees}")

        if total_referees == 6:
            print("✅ SUCCESS: All 6 referees found in Pass 1!")
        else:
            print(f"❌ FAILURE: Expected 6 referees, found {total_referees}")

        # Show current page state after Pass 1
        current_id = extractor.get_current_manuscript_id()
        print(f"\n📍 Current manuscript after Pass 1: {current_id}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        if hasattr(extractor, "driver") and extractor.driver:
            extractor.driver.quit()


if __name__ == "__main__":
    test_pass1_only()
