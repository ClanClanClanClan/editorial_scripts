#!/usr/bin/env python3
"""
COMPARE MF vs MOR URLs
======================

Test if both MF and MOR URLs are valid and reachable.
"""

import sys
from pathlib import Path
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def test_url_accessibility():
    """Test if both MF and MOR URLs are accessible."""
    print("🌐 Testing URL accessibility...")

    urls = {
        "MF": "https://mc.manuscriptcentral.com/mafi",
        "MOR": "https://mc.manuscriptcentral.com/mathor"
    }

    # Test with requests first
    print("\n📡 Testing with HTTP requests...")
    for name, url in urls.items():
        try:
            response = requests.get(url, timeout=10)
            print(f"✅ {name}: {url} → Status {response.status_code}")
        except Exception as e:
            print(f"❌ {name}: {url} → Error: {e}")

    # Test with browser
    print("\n🌐 Testing with browser...")
    options = Options()
    options.add_argument("--headless")  # Run headless for this test
    driver = webdriver.Chrome(options=options)

    try:
        for name, url in urls.items():
            try:
                print(f"🔍 Testing {name}: {url}")
                driver.get(url)
                title = driver.title
                current_url = driver.current_url
                print(f"   📄 Title: {title}")
                print(f"   📍 Final URL: {current_url}")

                # Check if it looks like a login page
                page_source = driver.page_source.lower()
                has_login = "login" in page_source
                has_password = "password" in page_source
                has_error = "error" in page_source or "not found" in page_source

                print(f"   🔐 Has login elements: {has_login}")
                print(f"   🔑 Has password field: {has_password}")
                print(f"   ❌ Has error indicators: {has_error}")
                print()

            except Exception as e:
                print(f"   ❌ Error loading {name}: {e}")
                print()

    finally:
        driver.quit()

if __name__ == "__main__":
    test_url_accessibility()