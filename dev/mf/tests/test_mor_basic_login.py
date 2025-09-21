#!/usr/bin/env python3
"""
TEST MOR BASIC LOGIN - Find where MOR fails
============================================

Simple test to see exactly where MOR breaks down.
"""

import sys
from pathlib import Path

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

try:
    from mor_extractor import ComprehensiveMORExtractor
    print("✅ MOR extractor imported successfully")
except ImportError as e:
    print(f"❌ Could not import MOR extractor: {e}")
    sys.exit(1)

def test_mor_basic_navigation():
    """Test just the basic MOR navigation."""
    print("🚀 Testing MOR basic navigation...")

    try:
        # Create extractor
        print("📝 Creating MOR extractor...")
        extractor = ComprehensiveMORExtractor()

        # Browser is already set up in __init__, just check if driver exists
        print("🌐 Checking browser setup...")
        if not hasattr(extractor, 'driver') or extractor.driver is None:
            print("❌ No driver found!")
            return False

        # Navigate to MOR
        print("🔍 Navigating to MOR start page...")
        extractor.driver.get("https://mc.manuscriptcentral.com/mathor")

        # Check what page we land on
        current_url = extractor.driver.current_url
        page_title = extractor.driver.title

        print(f"📍 Current URL: {current_url}")
        print(f"📄 Page title: {page_title}")

        # Check if we can find login elements
        print("🔍 Looking for login elements...")

        # Common login selectors
        login_selectors = [
            ("id", "loginName"),
            ("name", "loginName"),
            ("id", "USER"),
            ("name", "USER"),
            ("class", "login-field"),
            ("xpath", "//input[@type='text']"),
            ("xpath", "//input[contains(@placeholder, 'email')]")
        ]

        login_found = False
        for selector_type, selector_value in login_selectors:
            try:
                if selector_type == "id":
                    element = extractor.driver.find_element("id", selector_value)
                elif selector_type == "name":
                    element = extractor.driver.find_element("name", selector_value)
                elif selector_type == "class":
                    element = extractor.driver.find_element("class name", selector_value)
                elif selector_type == "xpath":
                    element = extractor.driver.find_element("xpath", selector_value)

                if element:
                    print(f"✅ Found login element: {selector_type}='{selector_value}'")
                    login_found = True
                    break

            except Exception as e:
                print(f"   ❌ No element found for {selector_type}='{selector_value}': {e}")

        if not login_found:
            print("❌ No login elements found!")

            # Check page source for clues
            page_source = extractor.driver.page_source
            if "login" in page_source.lower():
                print("📝 Page contains 'login' text")
            if "password" in page_source.lower():
                print("📝 Page contains 'password' text")
            if "error" in page_source.lower():
                print("⚠️ Page contains 'error' text")
            if "maintenance" in page_source.lower():
                print("🚧 Page contains 'maintenance' text")

            # Save page source for debugging
            with open("/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/dev/mf/debug/mor_page_source.html", "w") as f:
                f.write(page_source)
            print("💾 Saved page source to dev/mf/debug/mor_page_source.html")

        # Cleanup
        print("🧹 Cleaning up browser...")
        extractor.cleanup()

        return login_found

    except Exception as e:
        print(f"❌ Error during MOR navigation test: {e}")
        try:
            extractor.cleanup()
        except:
            pass
        return False

if __name__ == "__main__":
    success = test_mor_basic_navigation()
    if success:
        print("✅ MOR basic navigation works")
    else:
        print("❌ MOR basic navigation failed")