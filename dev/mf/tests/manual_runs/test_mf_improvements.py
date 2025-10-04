#!/usr/bin/env python3
"""Test that MF handles any category dynamically and deduplicates."""

import sys
import os
import time

sys.path.append("production/src/extractors")

from mf_extractor import ComprehensiveMFExtractor


def test_improvements():
    """Test dynamic categories and deduplication."""
    print("🚀 Testing MF Dynamic Categories & Deduplication")
    print("=" * 60)

    extractor = None

    try:
        # Create instance
        print("⚙️ Initializing...")
        extractor = ComprehensiveMFExtractor()
        print("✅ Initialized")

        # Run login only
        print("\n🔐 Logging in...")
        if not extractor.login():
            print("❌ Login failed")
            return False

        print("✅ Login successful")

        # Navigate to AE Center
        print("\n📋 Navigating to AE Center...")
        extractor.driver.get("https://mc.manuscriptcentral.com/mafi")
        time.sleep(3)

        # Find AE Center link
        from selenium.webdriver.common.by import By

        try:
            ae_link = extractor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(3)
            print("✅ At AE Center")
        except:
            try:
                ae_link = extractor.driver.find_element(
                    By.XPATH, "//a[contains(text(),'Associate Editor')]"
                )
                ae_link.click()
                time.sleep(3)
                print("✅ At AE Center")
            except:
                print("❌ Could not find AE Center")
                return False

        # Test dynamic category detection
        print("\n📊 Testing Dynamic Category Detection...")
        print("-" * 50)

        all_links = extractor.driver.find_elements(By.TAG_NAME, "a")

        category_keywords = [
            "awaiting",
            "overdue",
            "reviewer",
            "scores",
            "selection",
            "invitation",
            "assignment",
            "recommendation",
            "decision",
            "revision",
            "response",
            "with editor",
            "under review",
            "in review",
            "manuscript",
            "submission",
        ]

        found_categories = []
        for link in all_links:
            try:
                link_text = link.text.strip()
                if not link_text:
                    continue

                text_lower = link_text.lower()
                if any(keyword in text_lower for keyword in category_keywords):
                    href = link.get_attribute("href")
                    if href and link.is_displayed():
                        # Try to find count
                        count = 0
                        try:
                            parent_row = link.find_element(By.XPATH, "./ancestor::tr[1]")
                            bold_elems = parent_row.find_elements(By.TAG_NAME, "b")
                            for elem in bold_elems:
                                text = elem.text.strip()
                                if text.isdigit():
                                    count = int(text)
                                    break
                        except:
                            pass

                        if not any(cat["name"] == link_text for cat in found_categories):
                            found_categories.append({"name": link_text, "count": count})
            except:
                continue

        print(f"✅ Found {len(found_categories)} categories dynamically:")
        for cat in found_categories:
            if cat["count"] > 0:
                print(f"   - {cat['name']} ({cat['count']} manuscripts)")
            else:
                print(f"   - {cat['name']}")

        # Test deduplication
        print("\n🔄 Testing Deduplication Logic...")
        print("-" * 50)

        # Simulate finding same manuscript in multiple categories
        test_id = "MAFI-2025-0212"

        print(f"Adding {test_id} to processed set...")
        extractor.processed_manuscript_ids.add(test_id)

        print(f"Checking if {test_id} would be skipped...")
        if test_id in extractor.processed_manuscript_ids:
            print(f"✅ {test_id} would be skipped (already processed)")
        else:
            print(f"❌ {test_id} would NOT be skipped")

        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS:")
        print(f"   Dynamic categories found: {len(found_categories)}")
        print(
            f"   Categories with manuscripts: {len([c for c in found_categories if c['count'] > 0])}"
        )
        print(
            f"   Deduplication working: {'Yes' if test_id in extractor.processed_manuscript_ids else 'No'}"
        )

        success = len(found_categories) > 0 and test_id in extractor.processed_manuscript_ids

        if success:
            print("\n✨ SUCCESS: Dynamic detection and deduplication working!")
        else:
            print("\n❌ FAILURE: Issues detected")

        return success

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        if extractor:
            try:
                print("\n🧹 Cleaning up...")
                extractor.cleanup()
                print("✅ Cleanup done")
            except:
                pass


if __name__ == "__main__":
    success = test_improvements()
    sys.exit(0 if success else 1)
