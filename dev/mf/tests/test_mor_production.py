#!/usr/bin/env python3
"""
TEST MOR PRODUCTION - Test the production MOR extractor
========================================================
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

from mor_extractor import ComprehensiveMORExtractor

print("🚀 TESTING PRODUCTION MOR EXTRACTOR")
print("=" * 70)

# Create output directory
output_dir = Path(__file__).parent.parent / 'outputs'
output_dir.mkdir(exist_ok=True)

extraction_results = {
    'timestamp': datetime.now().isoformat(),
    'extractor': 'MOR',
    'categories': [],
    'manuscripts': [],
    'errors': []
}

mor = ComprehensiveMORExtractor()

try:
    print("🔐 Logging in...")
    if not mor.login():
        print("❌ Login failed!")
        extraction_results['errors'].append("Login failed")
    else:
        print("✅ Login successful!")

        # Extract manuscripts
        print("\n📄 EXTRACTING MANUSCRIPTS...")
        manuscripts = mor.extract_all()

        if manuscripts:
            extraction_results['manuscripts'] = manuscripts
            print(f"\n✅ Extracted {len(manuscripts)} manuscripts:")
            for ms in manuscripts:
                print(f"   • {ms.get('id', 'Unknown')} - {ms.get('title', 'No title')[:50]}")
                if 'category' in ms:
                    print(f"     Category: {ms['category']}")
        else:
            print("❌ No manuscripts extracted")

            # Try manual extraction
            print("\n🔍 Trying manual category extraction...")

            # Navigate to AE Center
            from selenium.webdriver.common.by import By
            ae_link = mor.safe_find_element(By.LINK_TEXT, "Associate Editor Center")
            if ae_link:
                mor.safe_click(ae_link)
                mor.smart_wait(5)

                # Get categories
                categories = mor.get_manuscript_categories()
                extraction_results['categories'] = categories

                if categories:
                    print(f"✅ Found {len(categories)} categories:")
                    for cat in categories:
                        print(f"   • {cat['name']}: {cat['count']} manuscripts")

                    # Extract from each category
                    for category in categories:
                        if category['count'] > 0:
                            print(f"\n📁 Extracting from {category['name']}...")

                            # Click on the category
                            cat_manuscripts = mor.get_manuscripts_from_category(category['name'])

                            if cat_manuscripts:
                                print(f"   ✅ Found {len(cat_manuscripts)} manuscripts")
                                for ms in cat_manuscripts:
                                    ms['category'] = category['name']
                                    extraction_results['manuscripts'].append(ms)
                                    print(f"      • {ms.get('id', 'Unknown')}")

except Exception as e:
    print(f"\n❌ Fatal error: {e}")
    extraction_results['errors'].append(f"Fatal: {str(e)}")

finally:
    print("\n🧹 Cleaning up...")
    mor.cleanup()

# Save results
output_file = output_dir / f"mor_production_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w') as f:
    json.dump(extraction_results, f, indent=2)

print("\n" + "=" * 70)
print(f"💾 Results saved to: {output_file}")
print(f"✅ Categories found: {len(extraction_results['categories'])}")
print(f"✅ Manuscripts extracted: {len(extraction_results['manuscripts'])}")

if extraction_results['errors']:
    print(f"⚠️ Errors: {len(extraction_results['errors'])}")

# Display results
if extraction_results['manuscripts']:
    print("\n📄 MOR MANUSCRIPTS:")
    for ms in extraction_results['manuscripts']:
        ms_id = ms.get('id', 'Unknown')
        category = ms.get('category', 'Unknown category')
        print(f"   • {ms_id} ({category})")

    if len(extraction_results['manuscripts']) == 2:
        print("\n✅ SUCCESS: Found both MOR manuscripts!")
    else:
        print(f"\n⚠️ Found {len(extraction_results['manuscripts'])} manuscripts (expected 2)")
else:
    print("\n❌ No manuscripts extracted")

print("\n🏁 DONE")