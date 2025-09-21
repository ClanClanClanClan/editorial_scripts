#!/usr/bin/env python3
"""
Test the complete 3-pass system as described by user:
Pass 1: referees, PDFs, abstracts, cover letters (main page)
Pass 2: "Manuscript Information" tab for authors, submission details
Pass 3: "Audit Trail" tab for timeline/correspondence
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

import time

from selenium.webdriver.common.by import By

from src.extractors.mf_extractor import ComprehensiveMFExtractor


def test_3_pass_system():
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
                    print(
                        f"🧪 TESTING 3-PASS SYSTEM ON CATEGORY: {category['name']} ({category['count']} manuscripts)"
                    )
                    print("=" * 70)

                    # USE THE ACTUAL 3-PASS EXTRACTION METHOD
                    extractor.execute_3_pass_extraction(category)

                    print("\n✅ 3-PASS SYSTEM TEST COMPLETE!")
                    print("=" * 70)
                    print("📊 Final Results:")
                    print(f"   📚 Total manuscripts processed: {len(extractor.manuscripts)}")
                    for i, ms in enumerate(extractor.manuscripts):
                        print(f"   📄 Manuscript {i+1}: {ms.get('id', 'UNKNOWN')}")
                        print(f"      👥 Referees: {len(ms.get('referees', []))}")
                        print(
                            f"      📄 Documents: {len([k for k, v in ms.get('documents', {}).items() if v])}"
                        )
                        print(f"      👤 Authors: {len(ms.get('authors', []))}")
                        print(f"      📅 Timeline: {len(ms.get('timeline', []))}")

                    break

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\n⏸️ Closing browser in 15 seconds...")
        time.sleep(15)
        extractor.driver.quit()


if __name__ == "__main__":
    test_3_pass_system()
