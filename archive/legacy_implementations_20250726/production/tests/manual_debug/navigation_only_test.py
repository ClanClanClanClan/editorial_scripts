#!/usr/bin/env python3
"""
Test navigation only - bypass all complex extraction
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


def navigation_test():
    """Test only navigation - no complex extraction"""
    print("🚗 NAVIGATION TEST ONLY")

    extractor = ComprehensiveMFExtractor()

    try:
        # Step 1: Login
        print("\n1️⃣ Login...")
        if not extractor.login():
            print("❌ Login failed")
            return False
        print("   ✅ Login successful")

        # Step 2: Navigate to AE Center
        print("\n2️⃣ Navigate to AE Center...")
        if not extractor.navigate_to_ae_center():
            print("❌ Navigation failed")
            return False
        print("   ✅ Navigation successful")

        # Step 3: Get categories (quick test)
        print("\n3️⃣ Get categories...")
        categories = extractor.get_manuscript_categories()
        print(f"   ✅ Found {len(categories)} categories")

        # Step 4: Click category
        print("\n4️⃣ Click target category...")
        target = None
        for cat in categories:
            if "Awaiting" in cat["name"]:
                target = cat
                break

        if not target:
            print("❌ No target category")
            return False

        target["link"].click()
        time.sleep(3)
        print("   ✅ Category clicked")

        # Step 5: Click Take Action
        print("\n5️⃣ Click Take Action...")
        links = extractor.driver.find_elements(
            By.XPATH, "//a[contains(@href,'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]"
        )

        if not links:
            print("❌ No Take Action links")
            return False

        links[0].click()
        time.sleep(5)
        print("   ✅ Take Action clicked")

        # Step 6: Get manuscript IDs (minimal)
        print("\n6️⃣ Get manuscript IDs...")

        # Just get current manuscript ID
        current_id = extractor.get_current_manuscript_id()
        print(f"   Manuscript 1: {current_id}")

        # Navigate to next and get ID
        print("\n7️⃣ Navigate to manuscript 2...")
        extractor.click_next_document()

        next_id = extractor.get_current_manuscript_id()
        print(f"   Manuscript 2: {next_id}")

        # Step 7: Count referee rows (no extraction)
        print("\n8️⃣ Count referee rows on each manuscript...")

        # Go back to manuscript 1
        extractor.click_previous_document()

        # Count referee rows on manuscript 1
        rows1 = extractor.driver.find_elements(By.XPATH, "//tr[.//a[contains(@href,'mailpopup')]]")
        print(f"   Manuscript 1 ({current_id}): {len(rows1)} mailpopup rows")

        # Go to manuscript 2
        extractor.click_next_document()

        # Count referee rows on manuscript 2
        rows2 = extractor.driver.find_elements(By.XPATH, "//tr[.//a[contains(@href,'mailpopup')]]")
        print(f"   Manuscript 2 ({next_id}): {len(rows2)} mailpopup rows")

        print("\n✅ NAVIGATION TEST COMPLETED SUCCESSFULLY!")
        print("   Navigation works, referee extraction must be the issue")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        print("\n⏰ Closing...")
        if hasattr(extractor, "driver") and extractor.driver:
            extractor.driver.quit()


if __name__ == "__main__":
    success = navigation_test()
    print(f"\n🎯 RESULT: {'SUCCESS' if success else 'FAILURE'}")
    sys.exit(0 if success else 1)
