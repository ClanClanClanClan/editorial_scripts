#!/usr/bin/env python3
"""
Test the detailed extraction and show each referee's detailed data
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import time

from selenium.webdriver.common.by import By

from src.extractors.mf_extractor import ComprehensiveMFExtractor


def test_detailed_extraction():
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

                        manuscript = {"id": manuscript_id, "referees": []}

                        print(f"🧪 TESTING DETAILED EXTRACTION FOR {manuscript_id}")
                        print("=" * 70)

                        extractor.extract_referees_comprehensive(manuscript)

                        print("\n📊 DETAILED RESULTS:")
                        print("=" * 70)

                        referees = manuscript.get("referees", [])

                        for i, referee in enumerate(referees, 1):
                            print(f"\n👤 REFEREE {i}: {referee['name']}")
                            print(f"   📧 Email: {referee['email']}")
                            print(f"   🏢 Affiliation: {referee['affiliation']}")
                            print(f"   🌍 Country: {referee['country']}")
                            print(f"   📊 Status: {referee['status']}")
                            print(f"   🆔 ORCID: {referee['orcid']}")
                            print(f"   📅 Dates: {referee['dates']}")
                            print(f"   🔗 Review Links: {len(referee['review_links'])} found")

                        print("\n✅ Test complete!")
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
    test_detailed_extraction()
