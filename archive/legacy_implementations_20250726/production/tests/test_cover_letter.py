#!/usr/bin/env python3
"""
Test cover letter extraction specifically
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import time

from selenium.webdriver.common.by import By

from src.extractors.mf_extractor import ComprehensiveMFExtractor


def test_cover_letter():
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

                        manuscript = {"id": manuscript_id, "documents": {}}

                        print(f"🧪 TESTING COVER LETTER EXTRACTION FOR {manuscript_id}")
                        print("=" * 70)

                        # Test document links extraction
                        print("📋 Testing document extraction...")
                        extractor.extract_document_links(manuscript)

                        print("\n📊 RESULTS:")
                        print("=" * 50)
                        docs = manuscript.get("documents", {})
                        print(f"Documents found: {docs}")

                        if docs.get("cover_letter"):
                            print("✅ Cover letter found and processed!")
                            if docs.get("cover_letter_path"):
                                print(f"   Path: {docs['cover_letter_path']}")
                        else:
                            print("❌ Cover letter not found")

                            # Debug: Look for cover letter links manually
                            print("\n🔍 DEBUG: Looking for cover letter links...")
                            try:
                                doc_section = extractor.driver.find_element(
                                    By.XPATH, "//p[@class='pagecontents msdetailsbuttons']"
                                )
                                all_links = doc_section.find_elements(By.TAG_NAME, "a")
                                print(f"Found {len(all_links)} links in document section:")
                                for i, link in enumerate(all_links):
                                    text = link.text.strip()
                                    href = link.get_attribute("href")
                                    print(f"  {i+1}. Text: '{text}' | Href: {href[:50]}...")
                            except Exception as e:
                                print(f"   ⚠️ Could not find document section: {e}")

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
    test_cover_letter()
