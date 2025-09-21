#!/usr/bin/env python3
"""
FIND NAVIGATION WITH ALERT HANDLING - Handle alerts and find navigation
======================================================================
"""

import sys
import time
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoAlertPresentException, UnexpectedAlertPresentException

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

from mf_extractor import ComprehensiveMFExtractor

def handle_alert(driver):
    """Handle any alert that might be present."""
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        print(f"   ⚠️ Alert detected: {alert_text}")
        alert.accept()
        print(f"   ✅ Alert dismissed")
        time.sleep(2)
        return True
    except NoAlertPresentException:
        return False

print("🔍 FINDING NAVIGATION OPTIONS WITH ALERT HANDLING")
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

# Handle any alerts
print("\n🔍 Checking for alerts...")
for _ in range(3):  # Try multiple times as alerts can appear with delay
    if handle_alert(mf.driver):
        time.sleep(2)

# Now check the page after handling alerts
print(f"\n📍 Current URL after alert handling: {mf.driver.current_url}")
print(f"📄 Page title after alert handling: {mf.driver.title}")

# Save screenshot
debug_dir = Path(__file__).parent.parent / 'debug'
debug_dir.mkdir(exist_ok=True)
screenshot = debug_dir / 'navigation_after_alert.png'
mf.driver.save_screenshot(str(screenshot))
print(f"\n📸 Screenshot saved: {screenshot}")

# Try to find links with alert handling
print("\n🔍 Finding ALL links on the page...")
try:
    all_links = mf.driver.find_elements(By.TAG_NAME, "a")
    print(f"Found {len(all_links)} total links")
except UnexpectedAlertPresentException:
    print("   ⚠️ Another alert appeared, handling...")
    handle_alert(mf.driver)
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
                if any(word in text.lower() for word in ['associate', 'editor', 'manuscript', 'review', 'awaiting', 'decision']):
                    print(f"     ⭐ IMPORTANT: {href[:100]}")
    except:
        pass

print(f"\nTotal text links found: {len(text_links)}")

# Look for role selection
print("\n🎯 Looking for role selection...")
role_patterns = [
    "Associate Editor", "Editor Center", "Author", "Reviewer",
    "Admin", "Publisher", "Dashboard", "Home"
]

for pattern in role_patterns:
    try:
        elements = mf.driver.find_elements(By.PARTIAL_LINK_TEXT, pattern)
        if elements:
            print(f"   ✅ Found: {pattern} ({len(elements)} occurrences)")
            for elem in elements[:2]:
                try:
                    href = elem.get_attribute('href')
                    print(f"      URL: {href[:100]}...")
                except:
                    pass
    except:
        pass

# Check for select dropdowns (role selection)
print("\n🔍 Checking for role selection dropdowns...")
try:
    selects = mf.driver.find_elements(By.TAG_NAME, "select")
    for select in selects:
        try:
            name = select.get_attribute('name') or ''
            id_attr = select.get_attribute('id') or ''
            options = select.find_elements(By.TAG_NAME, "option")
            if options:
                print(f"   📋 Dropdown found: {name or id_attr}")
                for opt in options[:5]:
                    print(f"      • {opt.text}")
        except:
            pass
except:
    pass

# Check for frames with role content
print("\n🔍 Checking frames for role content...")
frames = mf.driver.find_elements(By.TAG_NAME, "frame")
iframes = mf.driver.find_elements(By.TAG_NAME, "iframe")

if frames or iframes:
    print(f"   Found {len(frames)} frames and {len(iframes)} iframes")

    for i, frame in enumerate((frames + iframes)[:3]):
        try:
            print(f"   📐 Checking frame {i+1}...")
            mf.driver.switch_to.frame(frame)

            # Look for links in frame
            frame_links = mf.driver.find_elements(By.TAG_NAME, "a")
            for link in frame_links[:10]:
                try:
                    text = link.text.strip()
                    if text and any(word in text.lower() for word in ['editor', 'manuscript', 'associate']):
                        print(f"      ✅ Found in frame: {text}")
                except:
                    pass

            mf.driver.switch_to.default_content()
        except Exception as e:
            print(f"      ❌ Could not check frame: {e}")
            try:
                mf.driver.switch_to.default_content()
            except:
                pass

# Save page source
with open(debug_dir / 'navigation_after_alert.html', 'w') as f:
    f.write(mf.driver.page_source)
print(f"\n💾 Page source saved: {debug_dir / 'navigation_after_alert.html'}")

print("\n🧹 Cleaning up...")
mf.cleanup()
print("✅ Navigation discovery complete")