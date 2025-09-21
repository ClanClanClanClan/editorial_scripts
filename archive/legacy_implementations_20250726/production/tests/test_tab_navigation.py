#!/usr/bin/env python3
"""
Test tab navigation with the correct image-based selectors
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import time

from selenium.webdriver.common.by import By

from src.extractors.mf_extractor import ComprehensiveMFExtractor


def test_tab_navigation():
    extractor = ComprehensiveMFExtractor()

    try:
        # Quick login and navigation
        login_success = extractor.login()
        if not login_success:
            return

        max_wait = 30
        wait_count = 0
        while wait_count < max_wait:
            current_url = extractor.driver.current_url
            if "page=LOGIN" not in current_url and "login" not in current_url.lower():
                break
            time.sleep(2)
            wait_count += 1

        time.sleep(3)
        ae_link = extractor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        ae_link.click()
        time.sleep(5)

        categories = extractor.get_manuscript_categories()
        if categories:
            for category in categories:
                if category["count"] > 0:
                    category["link"].click()
                    time.sleep(3)

                    take_action_links = extractor.driver.find_elements(
                        By.XPATH, "//a[contains(@href,'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]"
                    )

                    if take_action_links:
                        take_action_links[0].click()
                        time.sleep(5)

                        manuscript_id = extractor.get_current_manuscript_id()
                        print(f"🧪 TESTING TAB NAVIGATION FOR {manuscript_id}")
                        print("=" * 70)

                        # Test 1: Navigate to Manuscript Information tab
                        print("\n📋 TEST 1: Manuscript Information Tab")
                        print("-" * 50)

                        success = extractor.navigate_to_manuscript_info_tab(manuscript_id)
                        if success:
                            print("✅ Successfully navigated to Manuscript Information tab!")

                            # Check what's on this tab
                            print("\n🔍 Looking for author information...")
                            author_elements = extractor.driver.find_elements(
                                By.XPATH,
                                "//*[contains(text(), 'Author') or contains(text(), 'Corresponding')]",
                            )
                            print(f"   Found {len(author_elements)} author-related elements")

                            # Navigate back to main tab
                            print("\n🔙 Going back to main page...")
                            extractor.navigate_to_main_page(manuscript_id)
                        else:
                            print("❌ Failed to navigate to Manuscript Information tab")

                        # Test 2: Navigate to Audit Trail tab
                        print("\n📊 TEST 2: Audit Trail Tab")
                        print("-" * 50)

                        success = extractor.navigate_to_audit_trail_tab(manuscript_id)
                        if success:
                            print("✅ Successfully navigated to Audit Trail tab!")

                            # Check what's on this tab
                            print("\n🔍 Looking for audit trail information...")
                            audit_elements = extractor.driver.find_elements(
                                By.XPATH,
                                "//*[contains(text(), 'Date') or contains(text(), 'Action') or contains(text(), 'Email')]",
                            )
                            print(f"   Found {len(audit_elements)} audit-related elements")
                        else:
                            print("❌ Failed to navigate to Audit Trail tab")

                        print("\n✅ Tab navigation test complete!")
                        break
                    break

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\n⏸️ Closing browser in 10 seconds...")
        time.sleep(10)
        extractor.driver.quit()


if __name__ == "__main__":
    test_tab_navigation()
