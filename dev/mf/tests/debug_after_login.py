#!/usr/bin/env python3
"""
DEBUG AFTER LOGIN - See what's available after successful login
================================================================
"""

import sys
import time
from pathlib import Path

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

from mf_extractor import ComprehensiveMFExtractor

print("🔍 DEBUGGING MF AFTER LOGIN")
print("=" * 70)

mf = ComprehensiveMFExtractor()

print("🔐 Logging in...")
if not mf.login():
    print("❌ Login failed!")
    mf.cleanup()
    exit(1)

print("✅ Login successful!")

# Check current state
print("\n📍 Current state after login:")
print(f"   URL: {mf.driver.current_url}")
print(f"   Title: {mf.driver.title}")

# Look for navigation elements
print("\n🔍 Looking for navigation elements...")

# Common navigation selectors for ScholarOne
nav_selectors = [
    ("Associate Editor Center", "Associate Editor"),
    ("Editor Center", "Editor"),
    ("Admin Center", "Admin"),
    ("Author Center", "Author"),
    ("Reviewer Center", "Reviewer"),
    ("Manuscripts", "Manuscripts"),
    ("All Manuscripts", "All Manuscripts"),
    ("Awaiting Decision", "Decision"),
    ("Under Review", "Review"),
    ("View Submissions", "Submissions")
]

print("\n📋 Available navigation links:")
for text, desc in nav_selectors:
    try:
        element = mf.driver.find_element("partial link text", text)
        print(f"   ✅ Found: {text}")
    except:
        pass

# Try to find manuscript-related links
print("\n🔍 Looking for manuscript-related elements...")
try:
    # Find all links on the page
    links = mf.driver.find_elements("tag name", "a")
    print(f"   Found {len(links)} total links on page")

    # Filter for relevant links
    relevant_links = []
    for link in links[:50]:  # Check first 50 links
        try:
            text = link.text.strip()
            href = link.get_attribute('href') or ''

            # Look for manuscript-related text
            if any(keyword in text.lower() for keyword in ['manuscript', 'submission', 'review', 'decision', 'author', 'referee']):
                relevant_links.append((text, href))
                print(f"   📎 {text}: {href[:50]}...")
        except:
            pass

except Exception as e:
    print(f"   ❌ Error scanning links: {e}")

# Try clicking on Associate Editor Center if available
print("\n🎯 Attempting to navigate to Associate Editor Center...")
try:
    aec_link = mf.driver.find_element("partial link text", "Associate Editor")
    print("   ✅ Found Associate Editor link, clicking...")
    aec_link.click()
    time.sleep(3)

    print(f"   📍 New URL: {mf.driver.current_url}")
    print(f"   📄 New Title: {mf.driver.title}")

    # Now try to get categories
    print("\n📊 Attempting to get manuscript categories...")
    categories = mf.get_manuscript_categories()
    print(f"   ✅ Found {len(categories)} categories:")
    for cat in categories[:5]:
        print(f"      • {cat}")

except Exception as e:
    print(f"   ❌ Could not navigate to AEC: {e}")

# Take a screenshot
try:
    screenshot_path = Path(__file__).parent.parent / 'debug' / 'after_login.png'
    screenshot_path.parent.mkdir(exist_ok=True)
    mf.driver.save_screenshot(str(screenshot_path))
    print(f"\n📸 Screenshot saved to: {screenshot_path}")
except:
    pass

print("\n🧹 Cleaning up...")
mf.cleanup()
print("✅ Debug complete")