#!/usr/bin/env python3
"""
FIND NAVIGATION AFTER LOGIN - See what navigation options are available
======================================================================
"""

import sys
import time
from pathlib import Path
from selenium.webdriver.common.by import By

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

from mf_extractor import ComprehensiveMFExtractor

print("🔍 FINDING NAVIGATION OPTIONS AFTER LOGIN")
print("=" * 70)

mf = ComprehensiveMFExtractor()

print("🔐 Logging in...")
if not mf.login():
    print("❌ Login failed!")
    mf.cleanup()
    exit(1)

print("✅ Login successful!")
print(f"\n📍 Current URL: {mf.driver.current_url}")
print(f"📄 Page title: {mf.driver.title}")

# Save screenshot
debug_dir = Path(__file__).parent.parent / 'debug'
debug_dir.mkdir(exist_ok=True)
screenshot = debug_dir / 'navigation_after_login.png'
mf.driver.save_screenshot(str(screenshot))
print(f"\n📸 Screenshot saved: {screenshot}")

# Find ALL links on the page
print("\n🔍 Finding ALL links on the page...")
all_links = mf.driver.find_elements(By.TAG_NAME, "a")
print(f"Found {len(all_links)} total links")

# Filter for meaningful text links
print("\n📋 Links with text (first 50):")
text_links = []
for link in all_links:
    try:
        text = link.text.strip()
        href = link.get_attribute('href') or ''

        if text and len(text) > 2 and not text.startswith('http'):
            text_links.append((text, href))
            if len(text_links) <= 50:
                print(f"   • {text[:80]}")
                if 'associate' in text.lower() or 'editor' in text.lower() or 'manuscript' in text.lower():
                    print(f"     ⭐ IMPORTANT: {href[:100]}")
    except:
        pass

print(f"\nTotal text links found: {len(text_links)}")

# Look for specific navigation patterns
print("\n🎯 Looking for navigation elements...")
nav_patterns = [
    "Associate", "Editor", "Manuscript", "Review",
    "Dashboard", "Home", "Center", "Submissions",
    "Tasks", "Queue", "All", "My"
]

for pattern in nav_patterns:
    print(f"\n   Pattern: '{pattern}'")
    matching_links = [(t, h) for t, h in text_links if pattern.lower() in t.lower()]
    if matching_links:
        for text, href in matching_links[:3]:
            print(f"      ✅ {text}")
            print(f"         URL: {href[:100]}...")

# Check for frames or iframes
print("\n🔍 Checking for frames/iframes...")
frames = mf.driver.find_elements(By.TAG_NAME, "frame")
iframes = mf.driver.find_elements(By.TAG_NAME, "iframe")
print(f"   Frames: {len(frames)}")
print(f"   IFrames: {len(iframes)}")

# Check for any role-based navigation
print("\n🔍 Looking for role-based elements...")
try:
    # Look for elements that might indicate role
    role_indicators = mf.driver.find_elements(By.XPATH, "//*[contains(text(), 'Role') or contains(text(), 'role')]")
    for elem in role_indicators[:5]:
        print(f"   • {elem.text[:100]}")
except:
    pass

# Try to find manuscript counts
print("\n📊 Looking for manuscript counts...")
try:
    # Look for elements with numbers in parentheses or bold
    count_elements = mf.driver.find_elements(By.XPATH, "//b[number(.) = .]|//*[contains(text(), '(') and contains(text(), ')')]")
    for elem in count_elements[:10]:
        text = elem.text.strip()
        if text and any(c.isdigit() for c in text):
            print(f"   • {text}")
except:
    pass

# Check page source for hidden elements
print("\n🔍 Checking page source for hidden navigation...")
page_source = mf.driver.page_source
if "Associate Editor" in page_source:
    print("   ✅ 'Associate Editor' found in page source")
if "manuscriptcentral.com/mafi?NEXT_PAGE=" in page_source:
    print("   ✅ Navigation URLs found in page source")

# Save page source for analysis
with open(debug_dir / 'navigation_page_source.html', 'w') as f:
    f.write(mf.driver.page_source)
print(f"\n💾 Page source saved: {debug_dir / 'navigation_page_source.html'}")

print("\n🧹 Cleaning up...")
mf.cleanup()
print("✅ Navigation discovery complete")