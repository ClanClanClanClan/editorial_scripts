#!/usr/bin/env python3
"""
RUN FULL EXTRACTION - Navigate to AE Center and extract manuscripts
==================================================================
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from selenium.webdriver.common.by import By

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

from mf_extractor import ComprehensiveMFExtractor

def run_full_extraction():
    """Run complete MF extraction with proper navigation."""

    print("🚀 RUNNING FULL MF EXTRACTION")
    print("=" * 70)

    # Create output directory
    output_dir = Path(__file__).parent.parent / 'outputs'
    output_dir.mkdir(exist_ok=True)

    extraction_results = {
        'timestamp': datetime.now().isoformat(),
        'extractor': 'MF',
        'categories': [],
        'manuscripts': [],
        'errors': []
    }

    mf = ComprehensiveMFExtractor()

    try:
        print("🔐 Logging in to MF platform...")
        if not mf.login():
            print("❌ Login failed!")
            extraction_results['errors'].append("Login failed")
            return extraction_results

        print("✅ Login successful!")

        # Navigate to Associate Editor Center
        print("\n🎯 Navigating to Associate Editor Center...")
        try:
            # Find and click Associate Editor link
            ae_link = mf.driver.find_element(By.PARTIAL_LINK_TEXT, "Associate Editor")
            print(f"   ✅ Found AE link: {ae_link.text}")
            ae_link.click()
            time.sleep(5)

            print(f"   📍 Current URL: {mf.driver.current_url}")
            print(f"   📄 Page title: {mf.driver.title}")

        except Exception as e:
            print(f"   ❌ Could not navigate to AE Center: {e}")
            extraction_results['errors'].append(f"Navigation to AE Center failed: {e}")

            # Try alternative: direct navigation
            print("   🔄 Trying direct navigation...")
            mf.driver.get("https://mc.manuscriptcentral.com/mafi?NEXT_PAGE=ASSOCIATE_HOME")
            time.sleep(5)

        # Now get manuscript categories
        print("\n📊 GETTING MANUSCRIPT CATEGORIES...")

        # Look for manuscript links on the page
        print("   🔍 Scanning for manuscript categories...")
        all_links = mf.driver.find_elements(By.TAG_NAME, "a")

        # Common manuscript category patterns
        category_patterns = [
            "awaiting", "review", "manuscript", "submission", "decision",
            "referee", "score", "recommendation", "overdue", "revision"
        ]

        found_categories = []
        for link in all_links:
            try:
                text = link.text.strip()
                if not text or len(text) > 100:
                    continue

                # Check if this looks like a manuscript category
                text_lower = text.lower()
                if any(pattern in text_lower for pattern in category_patterns):
                    # Try to get count from parent row
                    count = 0
                    try:
                        # Find parent row
                        row = link.find_element(By.XPATH, "./ancestor::tr[1]")
                        row_text = row.text

                        # Look for numbers
                        import re
                        numbers = re.findall(r'\b(\d+)\b', row_text)
                        if numbers:
                            # Usually the count is the first or last number
                            count = int(numbers[0])
                    except:
                        pass

                    category_info = {
                        'name': text,
                        'count': count,
                        'href': link.get_attribute('href')
                    }

                    if text not in [c['name'] for c in found_categories]:
                        found_categories.append(category_info)
                        print(f"   ✅ Found category: {text} ({count} manuscripts)")

            except Exception as e:
                continue

        extraction_results['categories'] = found_categories
        print(f"\n✅ Found {len(found_categories)} categories")

        # Extract manuscripts from categories with items
        print("\n📄 EXTRACTING MANUSCRIPTS...")

        manuscripts_extracted = 0
        max_manuscripts = 3  # Limit for testing

        for category in found_categories:
            if manuscripts_extracted >= max_manuscripts:
                break

            if category['count'] > 0:
                print(f"\n📁 Checking category: {category['name']}")

                try:
                    # Click on the category link
                    cat_link = mf.driver.find_element(By.LINK_TEXT, category['name'])
                    cat_link.click()
                    time.sleep(3)

                    # Look for manuscript IDs on the page
                    print("   🔍 Looking for manuscript IDs...")

                    # Common patterns for manuscript IDs
                    ms_links = mf.driver.find_elements(By.PARTIAL_LINK_TEXT, "MF-")

                    if not ms_links:
                        # Try alternative patterns
                        all_links = mf.driver.find_elements(By.TAG_NAME, "a")
                        ms_links = [l for l in all_links if "MF-" in (l.text or "")]

                    print(f"   ✅ Found {len(ms_links)} manuscripts in this category")

                    for ms_link in ms_links[:2]:  # Limit to 2 per category
                        if manuscripts_extracted >= max_manuscripts:
                            break

                        try:
                            ms_id = ms_link.text.strip()
                            print(f"\n   📋 Extracting manuscript: {ms_id}")

                            # Click on manuscript
                            ms_link.click()
                            time.sleep(3)

                            # Extract basic details from the page
                            manuscript_data = {
                                'id': ms_id,
                                'category': category['name'],
                                'title': None,
                                'status': None,
                                'authors': [],
                                'referees': []
                            }

                            # Try to get title
                            try:
                                title_elem = mf.driver.find_element(By.XPATH, "//td[contains(text(),'Title:')]/following-sibling::td")
                                manuscript_data['title'] = title_elem.text.strip()
                            except:
                                pass

                            # Try to get status
                            try:
                                status_elem = mf.driver.find_element(By.XPATH, "//td[contains(text(),'Status:')]/following-sibling::td")
                                manuscript_data['status'] = status_elem.text.strip()
                            except:
                                pass

                            extraction_results['manuscripts'].append(manuscript_data)
                            manuscripts_extracted += 1

                            print(f"      ✅ Extracted: {ms_id}")
                            if manuscript_data['title']:
                                print(f"      📝 Title: {manuscript_data['title'][:50]}...")

                            # Go back to list
                            mf.driver.back()
                            time.sleep(2)

                        except Exception as e:
                            print(f"      ❌ Error extracting manuscript: {e}")
                            extraction_results['errors'].append(f"Failed to extract manuscript: {e}")

                    # Go back to categories
                    mf.driver.back()
                    time.sleep(2)

                except Exception as e:
                    print(f"   ❌ Error with category {category['name']}: {e}")
                    extraction_results['errors'].append(f"Category error {category['name']}: {e}")

        print(f"\n✅ Extracted {manuscripts_extracted} manuscripts")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        extraction_results['errors'].append(f"Fatal error: {e}")

    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        mf.cleanup()

    # Save results
    output_file = output_dir / f"full_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(extraction_results, f, indent=2)

    print("\n" + "=" * 70)
    print(f"💾 Results saved to: {output_file}")
    print(f"✅ Categories found: {len(extraction_results['categories'])}")
    print(f"✅ Manuscripts extracted: {len(extraction_results['manuscripts'])}")

    if extraction_results['errors']:
        print(f"⚠️ Errors occurred: {len(extraction_results['errors'])}")

    return extraction_results

if __name__ == "__main__":
    results = run_full_extraction()

    print("\n" + "=" * 70)
    print("📊 EXTRACTION SUMMARY")
    print("=" * 70)

    if results['categories']:
        print("\n📋 CATEGORIES FOUND:")
        for cat in results['categories'][:5]:
            print(f"   • {cat['name']} ({cat['count']} manuscripts)")

    if results['manuscripts']:
        print("\n📄 MANUSCRIPTS EXTRACTED:")
        for ms in results['manuscripts']:
            print(f"\n   📌 {ms['id']} in {ms['category']}")
            if ms.get('title'):
                print(f"      Title: {ms['title'][:60]}...")
            if ms.get('status'):
                print(f"      Status: {ms['status']}")
    else:
        print("\n❌ No manuscripts extracted")

    print("\n🏁 EXTRACTION COMPLETE")