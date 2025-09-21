#!/usr/bin/env python3
"""Quick test to verify MOR extractor is working."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "production", "src", "extractors"))

from mor_extractor import ComprehensiveMORExtractor


def test_mor_status():
    print("🧪 Testing MOR Extractor Status")
    print("=" * 60)

    extractor = ComprehensiveMORExtractor()

    try:
        # Test login
        print("🔐 Testing login...")
        if not extractor.login():
            print("❌ Login failed")
            return False
        print("✅ Login successful")

        # Quick navigation test
        import time

        from selenium.webdriver.common.by import By

        print("📋 Testing navigation...")
        ae_link = extractor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        ae_link.click()
        time.sleep(3)

        # Get categories
        categories = extractor.get_manuscript_categories()
        if not categories:
            print("❌ No categories found")
            return False

        print(f"✅ Found {len(categories)} categories")
        for cat in categories[:3]:  # Show first 3
            print(f"   - {cat['name']} ({cat['count']} manuscripts)")

        # Test extraction on 1 manuscript
        first_category = categories[0]
        first_category["count"] = 1  # Limit to 1
        print(f"\n📂 Testing extraction with: {first_category['name']}")

        extractor.process_category(first_category)

        if extractor.manuscripts:
            ms = extractor.manuscripts[0]
            print(f"\n📄 Manuscript: {ms.get('id', 'UNKNOWN')}")
            print(f"📝 Title: {ms.get('title', 'N/A')[:60]}...")

            # Check referees
            referees = ms.get("referees", [])
            emails_found = sum(1 for r in referees if r.get("email", ""))
            print(f"🧑‍⚖️ Referees: {len(referees)} total, {emails_found} with emails")

            # Check authors
            authors = ms.get("authors", [])
            author_emails = sum(1 for a in authors if a.get("email", ""))
            print(f"✍️ Authors: {len(authors)} total, {author_emails} with emails")

            print("\n" + "=" * 60)
            print("✅ MOR EXTRACTOR IS WORKING!")
            return True
        else:
            print("❌ No manuscripts extracted")
            return False

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        try:
            extractor.cleanup()
        except:
            pass


if __name__ == "__main__":
    success = test_mor_status()
    sys.exit(0 if success else 1)
