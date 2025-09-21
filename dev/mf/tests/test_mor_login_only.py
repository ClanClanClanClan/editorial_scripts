#!/usr/bin/env python3
"""
Test just the MOR login
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

# Check credentials first
print("Checking credentials...")
print(f"MOR_EMAIL: {'✅' if os.getenv('MOR_EMAIL') else '❌'}")
print(f"MOR_PASSWORD: {'✅' if os.getenv('MOR_PASSWORD') else '❌'}")

if not (os.getenv('MOR_EMAIL') and os.getenv('MOR_PASSWORD')):
    print("\n❌ Credentials not found. Loading from shell...")
    os.system("source ~/.editorial_scripts/load_all_credentials.sh")

from extractors.mor_extractor import MORExtractor
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

print("\n" + "="*60)
print("🔐 TESTING MOR LOGIN ONLY")
print("="*60)

mor = None
try:
    # Create instance
    print("\n1. Creating MOR instance...")
    mor = MORExtractor(use_cache=False)
    print("   ✅ Instance created")

    # Create driver manually
    print("\n2. Creating Chrome driver...")
    mor.driver = webdriver.Chrome(options=mor.chrome_options)
    mor.driver.set_page_load_timeout(30)
    mor.driver.implicitly_wait(10)
    mor.wait = WebDriverWait(mor.driver, 10)
    mor.original_window = mor.driver.current_window_handle
    print("   ✅ Driver created")

    # Test login
    print("\n3. Testing login...")
    login_result = mor.login()

    if login_result:
        print("   ✅ LOGIN SUCCESSFUL!")

        # Check where we are
        print("\n4. Checking current page...")
        print(f"   URL: {mor.driver.current_url}")
        print(f"   Title: {mor.driver.title}")

        # Check for AE Center link
        from selenium.webdriver.common.by import By
        ae_links = mor.driver.find_elements(By.XPATH, "//a[contains(text(), 'Associate Editor')]")
        print(f"   AE links found: {len(ae_links)}")

    else:
        print("   ❌ LOGIN FAILED")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if mor and hasattr(mor, 'driver'):
        try:
            mor.driver.quit()
            print("\n🧹 Driver closed")
        except:
            pass
    print("\n" + "="*60)
    print("LOGIN TEST COMPLETE")
    print("="*60)