#!/usr/bin/env python3
"""
Ultrathink focused test - just fix the referee extraction on manuscript 2
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


def ultrathink_test():
    """Focused test on referee extraction"""
    print("🧠 ULTRATHINK TEST: Focus on referee extraction")

    extractor = ComprehensiveMFExtractor()

    try:
        # Login and navigate (this part works)
        if not extractor.login():
            print("❌ Login failed")
            return

        if not extractor.navigate_to_ae_center():
            print("❌ Navigation failed")
            return

        # Get to manuscripts (this part works)
        categories = extractor.get_manuscript_categories()
        target_category = None
        for category in categories:
            if "Awaiting Reviewer Scores" in category["name"]:
                target_category = category
                break

        if not target_category:
            print("❌ No category found")
            return

        # Navigate to manuscripts
        target_category["link"].click()
        time.sleep(3)

        take_action_links = extractor.driver.find_elements(
            By.XPATH, "//a[contains(@href,'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]"
        )

        if len(take_action_links) < 2:
            print("❌ Need at least 2 manuscripts")
            return

        take_action_links[0].click()
        time.sleep(5)

        # Get manuscript order
        (
            manuscript_count,
            manuscript_data,
            manuscript_order,
        ) = extractor.extract_basic_manuscript_info()
        print(f"📄 Found manuscripts: {manuscript_order}")

        # FOCUSED TEST: Extract referees from manuscript 1
        print(f"\n🔬 Testing manuscript 1: {manuscript_order[0]}")
        manuscript1 = manuscript_data[manuscript_order[0]]

        current_id = extractor.get_current_manuscript_id()
        print(f"   Current page ID: {current_id}")

        extractor.extract_referees_comprehensive(manuscript1)
        print(f"   Manuscript 1 referees found: {len(manuscript1.get('referees', []))}")

        # Navigate to manuscript 2
        print("\n➡️ Navigating to manuscript 2...")
        extractor.click_next_document()

        # FOCUSED TEST: Extract referees from manuscript 2
        print(f"\n🔬 Testing manuscript 2: {manuscript_order[1]}")
        manuscript2 = manuscript_data[manuscript_order[1]]

        current_id = extractor.get_current_manuscript_id()
        print(f"   Current page ID: {current_id}")

        extractor.extract_referees_comprehensive(manuscript2)
        print(f"   Manuscript 2 referees found: {len(manuscript2.get('referees', []))}")

        # RESULT
        total_referees = len(manuscript1.get("referees", [])) + len(manuscript2.get("referees", []))
        print(f"\n📊 TOTAL REFEREES: {total_referees}")

        if total_referees == 6:
            print("✅ SUCCESS: All 6 referees found!")
        else:
            print(f"❌ FAILURE: Expected 6, got {total_referees}")

        return total_referees == 6

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        print("\n⏰ Closing browser in 10 seconds...")
        time.sleep(10)
        if hasattr(extractor, "driver") and extractor.driver:
            extractor.driver.quit()


if __name__ == "__main__":
    success = ultrathink_test()
    print(f"\n🎯 FINAL RESULT: {'SUCCESS' if success else 'FAILURE'}")
    sys.exit(0 if success else 1)
