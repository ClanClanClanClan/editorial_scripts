#!/usr/bin/env python3
"""
Basic Chrome driver test
"""

import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

print("Testing Chrome driver...")

try:
    print("1. Creating Chrome options...")
    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    print("   ✅ Options created")

    print("2. Creating Chrome driver...")
    driver = webdriver.Chrome(options=chrome_options)
    print("   ✅ Driver created")

    print("3. Loading a page...")
    driver.get("https://www.google.com")
    print("   ✅ Page loaded")

    print("4. Getting page title...")
    title = driver.title
    print(f"   ✅ Title: {title}")

    print("5. Closing driver...")
    driver.quit()
    print("   ✅ Driver closed")

    print("\n✅ Chrome driver is working!")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()